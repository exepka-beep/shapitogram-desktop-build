// Ядро TON-кошелька: генерация/импорт, адреса, переводы (V4-кошелёк).
// Использует публичный TON Center v2 API.

import { mnemonicNew, mnemonicValidate, mnemonicToPrivateKey } from "@ton/crypto";
import { TonClient, WalletContractV4, internal, toNano, fromNano, SendMode, NftItem } from "@ton/ton";
import { beginCell, Address, CommentMessage } from "@ton/core";
import type { KeyPair } from "@ton/crypto";

export const NETWORK_KEY = "shapito_ton_network";
export type Network = "mainnet" | "testnet";

const TONCENTER: Record<Network, string> = {
  mainnet: "https://toncenter.com/api/v2/jsonRPC",
  testnet: "https://testnet.toncenter.com/api/v2/jsonRPC",
};

// Публичные точки для TON API (балансы, jetton'ы, история) — read-only.
const TONAPI: Record<Network, string> = {
  mainnet: "https://tonapi.io",
  testnet: "https://testnet.tonapi.io",
};

export function getNetwork(): Network {
  return (localStorage.getItem(NETWORK_KEY) as Network) || "mainnet";
}

export function setNetwork(n: Network) {
  localStorage.setItem(NETWORK_KEY, n);
}

export function getClient(net: Network = getNetwork()): TonClient {
  return new TonClient({ endpoint: TONCENTER[net] });
}

export function tonapiBase(net: Network = getNetwork()): string {
  return TONAPI[net];
}

// ---------- Кошелёк ----------

export interface WalletAccount {
  mnemonic: string[];
  address: string;
  friendly: string;
  bounceable: string;
}

export async function createWallet(): Promise<WalletAccount> {
  const m = await mnemonicNew(24);
  return importWallet(m);
}

export async function importWallet(words: string[]): Promise<WalletAccount> {
  const normalized = words.map((w) => w.trim().toLowerCase()).filter(Boolean);
  if (normalized.length < 12) throw new Error("Seed-фраза должна быть 12 или 24 слова");
  if (!(await mnemonicValidate(normalized))) throw new Error("Невалидная seed-фраза");
  const kp = await mnemonicToPrivateKey(normalized);
  const wallet = WalletContractV4.create({ workchain: 0, publicKey: kp.publicKey });
  const addr = wallet.address;
  return {
    mnemonic: normalized,
    address: addr.toString(),
    friendly: addr.toString({ bounceable: true, urlSafe: true }),
    bounceable: addr.toString({ bounceable: true, urlSafe: true }),
  };
}

async function keyPairFrom(mnemonic: string[]): Promise<KeyPair> {
  return mnemonicToPrivateKey(mnemonic.map((w) => w.trim().toLowerCase()));
}

function walletFrom(kp: KeyPair) {
  return WalletContractV4.create({ workchain: 0, publicKey: kp.publicKey });
}

// ---------- Баланс и история ----------

export interface NativeBalance {
  amount: bigint;
  formatted: string;
}

export async function fetchBalance(address: string): Promise<NativeBalance> {
  const net = getNetwork();
  const url = `${tonapiBase(net)}/v2/accounts/${encodeURIComponent(address)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Не удалось получить баланс");
  const data = await res.json();
  const amount = BigInt(data.balance ?? 0);
  return { amount, formatted: fromNano(amount) };
}

export async function fetchTransactions(address: string) {
  const net = getNetwork();
  const url = `${tonapiBase(net)}/v2/accounts/${encodeURIComponent(address)}/events?limit=25`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Не удалось получить историю");
  const data = await res.json();
  return (data.events ?? []).map((e: any) => {
    const myAddr = address.toLowerCase();
    let direction: "in" | "out" = "in";
    let amount = "0";
    let comment = "";
    const act = e.actions?.[0] ?? {};
    const d = act.SimplePreview ?? act.TonTransfer;
    const details = act?.details ?? {};
    // Сообщения внутри события
    let value = 0n;
    for (const msg of e.event?.messages ?? []) {
      // исходящее и входящее
    }
    const transfer = act.TonTransfer ?? act.JettonTransfer;
    if (transfer) {
      amount = transfer.amount ?? "0";
      try {
        const v = BigInt(amount) / 1000000000n;
        amount = fromNano(v);
      } catch { /* ignore */ }
      comment = transfer.comment ?? "";
      const source = (transfer.sender?.address ?? "").toLowerCase();
      if (source && source === myAddr) direction = "out";
      if (act.RatingChange) direction = "out";
    } else {
      amount = "0";
    }
    return {
      id: e.event_id,
      time: e.timestamp,
      direction,
      amount,
      comment,
      status: e.actions?.every((a: any) => a.status === "ok") ? "ok" : "failed",
      raw: act,
    };
  });
}

// ---------- Перевод ----------

export interface SendInput {
  mnemonic: string[];
  to: string;
  amountTon: string;
  comment?: string;
}

export async function sendTon({ mnemonic, to, amountTon, comment }: SendInput): Promise<string> {
  const net = getNetwork();
  const client = getClient(net);
  const kp = await keyPairFrom(mnemonic);
  const wallet = walletFrom(kp);
  const seqno: number = await client.getContractSEQNO(wallet).catch(() => 0);

  const toAddr = Address.parse(to);
  let body = undefined as any;
  if (comment && comment.trim()) {
    body = beginCell().storeUint(0, 32).storeStringTail(comment.trim()).endCell();
  }

  const transfer = internal({
    to: toAddr,
    value: toNano(amountTon),
    bounce: false,
    body,
  });

  const opened = client.open(wallet);
  await opened.sendTransfer({
    seqno,
    secretKey: kp.secretKey,
    messages: [transfer],
    sendMode: SendMode.PAY_GAS_SEPARATELY,
  });
  return `Перевод ${amountTon} TON отправлен на ${to}`;
}

// ---------- Вычисление комиссии ----------

export async function estimateFee(to: string, amountTon: string, mnemonic: string[]): Promise<string> {
  try {
    const net = getNetwork();
    const client = getClient(net);
    const kp = await keyPairFrom(mnemonic);
    const wallet = walletFrom(kp);
    const opened = client.open(wallet);
    const seqno: number = await client.getContractSEQNO(wallet).catch(() => 0);
    const toAddr = Address.parse(to);
    const fee = await opened.getSendTransfer({
      seqno,
      secretKey: kp.secretKey,
      messages: [internal({ to: toAddr, value: toNano(amountTon), bounce: false })],
    });
    return fromNano(fee);
  } catch {
    return "~0.01";
  }
}

// ---------- Сохранение ----------

const STORE_KEY = "shapito_ton_wallet_v1";

export interface StoredWallet {
  mnemonic: string[];
  address: string;
  name?: string;
}

export function saveWallet(w: StoredWallet) {
  localStorage.setItem(STORE_KEY, JSON.stringify(w));
}

export function loadWallet(): StoredWallet | null {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function forgetWallet() {
  localStorage.removeItem(STORE_KEY);
}

export function shortAddress(a: string): string {
  if (!a) return "";
  if (a.length < 16) return a;
  return `${a.slice(0, 6)}…${a.slice(-6)}`;
}

export function walletName(w: StoredWallet): string {
  return w.name || "Основной";
}

// ---------- NFT (юзы, анонимные номера, подарки) ----------

export type NftCategory = "username" | "number" | "gift" | "other";

export interface NftItem {
  address: string;
  index: number;
  name: string;
  description: string;
  image: string;
  collectionAddress: string;
  collectionName: string;
  verified: boolean;
  category: NftCategory;
  onSale: boolean;
  salePriceTon: string;
  ownerAddress: string;
}

// TON Space классифицирует NFT по имени коллекции. Fragment-коллекции
// Telegram содержат в имени "Username" / "Anonymous" / "Gift".
function classify(collectionName: string, nftName: string): NftCategory {
  const c = collectionName.toLowerCase();
  const n = nftName.toLowerCase();
  if (c.includes("username") || c.includes("t.me username") || /^@?[a-z0-9_]{5,32}$/.test(nftName.replace(/^@/, "")) && c.includes("username")) {
    return "username";
  }
  if (c.includes("anonymous") || c.includes("number") || /^\+?\d[\d\s()]{7,}$/.test(nftName.replace(/^\+/, "")) && c.includes("anonymous")) {
    return "number";
  }
  if (c.includes("gift") || c.includes("plush") || c.includes("toy") || c.includes("pepe")) {
    return "gift";
  }
  return "other";
}

export async function fetchNfts(address: string): Promise<NftItem[]> {
  const net = getNetwork();
  const out: NftItem[] = [];
  let offset: number | undefined;
  for (let page = 0; page < 6; page++) {
    const params = new URLSearchParams({ limit: "100", indirect_ownership: "false" });
    if (offset !== undefined) params.set("offset", String(offset));
    const res = await fetch(`${tonapiBase(net)}/v2/accounts/${encodeURIComponent(address)}/nfts?${params}`);
    if (!res.ok) throw new Error("Не удалось получить NFT");
    const data = await res.json();
    for (const it of data.nft_items ?? []) {
      const meta = it.metadata ?? {};
      const collectionName = it.collection?.name ?? meta.collection ?? "";
      const name = meta.name ?? it.dns ?? "";
      const image = (meta.image && !meta.image.startsWith("http") ? `https://nft.fragment.com/` + meta.image : meta.image) ?? "";
      const sale = it.sale ?? {};
      out.push({
        address: it.address,
        index: it.index ?? 0,
        name,
        description: meta.description ?? "",
        image,
        collectionAddress: it.collection?.address ?? "",
        collectionName,
        verified: Boolean(it.verified),
        category: classify(collectionName, name),
        onSale: Boolean(it.on_sale && sale.price),
        salePriceTon: it.on_sale && sale.price ? fromNano(BigInt(sale.price.value ?? 0)) : "",
        ownerAddress: it.owner?.address ?? "",
      });
    }
    if (!data.next_from) break;
    offset = data.next_from;
  }
  return out;
}

// Перевод NFT на другой адрес кошелька (нативный transfer через NftItem).
export async function sendNft(input: {
  mnemonic: string[];
  nftAddress: string;
  newOwner: string;
  comment?: string;
}): Promise<string> {
  const net = getNetwork();
  const client = getClient(net);
  const kp = await keyPairFrom(input.mnemonic);
  const wallet = walletFrom(kp);
  const seqno: number = await client.getContractSEQNO(wallet).catch(() => 0);

  const nft = client.open(NftItem.createFromAddress(Address.parse(input.nftAddress)));
  const query = {
    newOwner: Address.parse(input.newOwner),
    responseDestination: wallet.address,
    customPayload: null as any,
    forwardAmount: toNano("0.05"),
    forwardPayload: input.comment && input.comment.trim()
      ? new CommentMessage(input.comment.trim())
      : null,
  };
  const fee = await nft.getTransfer(query);
  const filled = { ...query, value: fee };
  const request = await nft.sendTransfer(filled);

  await client.sendExternal({
    to: wallet.address,
    secretKey: kp.secretKey,
    seqno,
    message: beginCell()
      .storeUint(2, 8)
      .storeRef(request)
      .storeUint(0, 8)
      .endCell(),
    sendMode: SendMode.PAY_GAS_SEPARATELY,
  });
  return `NFT отправлен на ${input.newOwner}`;
}

// Ссылка на продажу: Fragment для юзов/номеров, Getgems для подарков.
export function sellUrl(nft: NftItem, network: Network = getNetwork()): string | null {
  if (network !== "mainnet") return null;
  if (nft.category === "username" || nft.category === "number") {
    const title = nft.name.replace(/^@/, "").replace(/^(\+?[\d\s()-]+)$/, "$1").trim();
    if (nft.category === "number") return `https://fragment.com/number/${encodeURIComponent(nft.name.replace(/^\+/, ""))}`;
    return `https://fragment.com/username/${encodeURIComponent(title)}`;
  }
  return `https://getgems.io/nft/${nft.address}`;
}

export function explorerUrl(address: string, network: Network = getNetwork()): string {
  return network === "mainnet"
    ? `https://tonviewer.com/${address}`
    : `https://testnet.tonviewer.com/${address}`;
}
