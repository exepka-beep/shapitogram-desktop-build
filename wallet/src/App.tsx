import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowDownLeft, ArrowUpRight, Copy, Eye, EyeOff, KeyRound, RefreshCw,
  Send, Settings, Shield, Wallet2, X, Check, Trash2, Link2, QrCode,
  Image as ImageIcon, AtSign, Hash, Gift as GiftIcon, ExternalLink, ShoppingBag, Coins,
  Phone, BadgeCheck,
} from "lucide-react";
import {
  createWallet, importWallet, fetchBalance, fetchTransactions, sendTon, estimateFee,
  saveWallet, loadWallet, forgetWallet, shortAddress, getNetwork, setNetwork,
  fetchNfts, sendNft, sellUrl, explorerUrl,
  type Network, type StoredWallet, type NftItem,
} from "./ton/wallet";
import { linkStatus, requestCode, confirmCode, unlinkAccount, accountTitle, type LinkedAccount } from "./ton/link";

type Screen = "home" | "send" | "receive" | "settings" | "seed" | "nfts" | "nftDetail" | "link";

interface Tx {
  id: string;
  time: number;
  direction: "in" | "out";
  amount: string;
  comment: string;
  status: string;
}

export default function App() {
  const [wallet, setWallet] = useState<StoredWallet | null>(() => loadWallet());
  const [screen, setScreen] = useState<Screen>("home");
  const [onboard, setOnboard] = useState<"none" | "create" | "import">(wallet ? "none" : "create");

  const [balance, setBalance] = useState("0.00");
  const [txs, setTxs] = useState<Tx[]>([]);
  const [nfts, setNfts] = useState<NftItem[]>([]);
  const [selectedNft, setSelectedNft] = useState<NftItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [hidden, setHidden] = useState(false);
  const [network, setNet] = useState<Network>(getNetwork());
  const [linkAccount, setLinkAccount] = useState<LinkedAccount | null>(null);
  const [linkChecked, setLinkChecked] = useState(false);

  const refresh = useCallback(async () => {
    if (!wallet) return;
    setLoading(true);
    try {
      const b = await fetchBalance(wallet.address);
      setBalance(b.formatted);
      const list = await fetchTransactions(wallet.address);
      setTxs(list as Tx[]);
      const nftList = await fetchNfts(wallet.address);
      setNfts(nftList);
    } catch (e) {
      console.warn(e);
    } finally {
      setLoading(false);
    }
  }, [wallet]);

  useEffect(() => {
    void refresh();
    const t = setInterval(() => void refresh(), 15000);
    return () => clearInterval(t);
  }, [refresh, network]);

  // Привязка аккаунта живёт на сервере и проверяется по адресу кошелька:
  // localStorage тут не источник истины.
  useEffect(() => {
    if (!wallet) {
      setLinkAccount(null);
      setLinkChecked(false);
      return;
    }
    let alive = true;
    setLinkChecked(false);
    linkStatus(wallet.address)
      .then((status) => {
        if (!alive) return;
        setLinkAccount(status.linked ? status.account ?? null : null);
        setLinkChecked(true);
      })
      .catch(() => {
        if (!alive) return;
        setLinkAccount(null);
        setLinkChecked(true);
      });
    return () => { alive = false; };
  }, [wallet]);

  const usd = useMemo(() => {
    const n = Number(balance.replace(/,/g, "")) || 0;
    const rate = 5.5; // приблизительный курс TON/USD
    return (n * rate).toFixed(2);
  }, [balance]);

  // ---------- Онбординг ----------
  if (onboard === "create" || onboard === "import") {
    return (
      <div className="onboard">
        <div className="onboard-card">
          <div className="brand">
            <Shield size={26} />
            <span>ShapitoTON</span>
          </div>
          <p className="onboard-sub">Кошелёк для ShapitoGram</p>
          <Onboarding
            mode={onboard}
            onDone={(w) => {
              saveWallet(w);
              setWallet(w);
              setOnboard("none");
            }}
          />
          {onboard === "create" && (
            <button className="link-btn" onClick={() => setOnboard("import")}>У меня уже есть seed-фраза</button>
          )}
        </div>
      </div>
    );
  }

  if (!wallet) {
    return (
      <div className="onboard">
        <div className="onboard-card">
          <div className="brand"><Shield size={26} /><span>ShapitoTON</span></div>
          <button className="btn primary big" onClick={() => setOnboard("create")}>Создать кошелёк</button>
          <button className="btn ghost big" onClick={() => setOnboard("import")}>Восстановить</button>
        </div>
      </div>
    );
  }

  // ---------- Основной интерфейс ----------
  return (
    <div className="app">
      <header className="topbar">
        <button className="icon-btn" onClick={() => setNet(network === "mainnet" ? "testnet" : "mainnet")} title={`Сеть: ${network}`}>
          <span className={`net-dot ${network}`} />
          <span className="net-label">{network === "mainnet" ? "TON" : "testnet"}</span>
        </button>
        <div className="topbar-title">ShapitoTON</div>
        <button className="icon-btn" onClick={() => setScreen("settings")}>
          <Settings size={20} />
        </button>
      </header>

      {screen === "home" && (
        <main className="home">
          <section className="wallet-card">
            <div className="wallet-row">
              <div className="wallet-name">
                <Wallet2 size={18} />
                <span>{wallet.name || "Основной"}</span>
              </div>
              <button className="icon-btn small" onClick={() => setHidden(!hidden)}>
                {hidden ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <div className="balance">
              <span className="amount">{hidden ? "•••••" : Number(balance).toLocaleString("ru-RU", { maximumFractionDigits: 4 })}</span>
              <span className="crypto">TON</span>
            </div>
            <div className="usd">≈ ${hidden ? "•••" : usd}</div>
            <div className="wallet-addr" onClick={() => { navigator.clipboard.writeText(wallet.address); }}>
              <code>{shortAddress(wallet.address)}</code>
              <Copy size={13} />
            </div>
          </section>

          <section className="actions">
            <ActionButton icon={<ArrowUpRight size={20} />} label="Отправить" onClick={() => setScreen("send")} />
            <ActionButton icon={<ArrowDownLeft size={20} />} label="Получить" onClick={() => setScreen("receive")} />
            <ActionButton icon={<ImageIcon size={20} />} label="NFT" badge={nfts.length || undefined} onClick={() => setScreen("nfts")} />
          </section>

          {linkChecked && (linkAccount ? (
            <button className="link-banner linked" onClick={() => setScreen("link")}>
              <BadgeCheck size={20} />
              <div className="link-banner-body">
                <strong>Аккаунт привязан</strong>
                <span>{accountTitle(linkAccount)}</span>
              </div>
            </button>
          ) : (
            <button className="link-banner" onClick={() => setScreen("link")}>
              <Phone size={20} />
              <div className="link-banner-body">
                <strong>Привязать аккаунт</strong>
                <span>По номеру телефона — подарки из блокчейна будут знать, кто их носит</span>
              </div>
            </button>
          ))}

          <section className="txs">
            <div className="section-head">
              <h2>История</h2>
              <button className="icon-btn small" onClick={() => void refresh()}>
                <RefreshCw size={15} className={loading ? "spin" : ""} />
              </button>
            </div>
            {txs.length === 0 ? (
              <div className="empty">Транзакций пока нет</div>
            ) : (
              <div className="tx-list">
                {txs.map((tx) => (
                  <div className="tx-row" key={tx.id}>
                    <div className={`tx-icon ${tx.direction}`}>
                      {tx.direction === "in" ? <ArrowDownLeft size={16} /> : <ArrowUpRight size={16} />}
                    </div>
                    <div className="tx-body">
                      <div className="tx-title">
                        {tx.direction === "in" ? "Получено" : "Отправлено"}
                        {tx.comment && <span className="tx-comment"> · {tx.comment.slice(0, 24)}</span>}
                      </div>
                      <div className="tx-date">{new Date(tx.time * 1000).toLocaleString("ru-RU")}</div>
                    </div>
                    <div className={`tx-amount ${tx.direction}`}>
                      {tx.direction === "in" ? "+" : "−"}{Number(tx.amount).toLocaleString("ru-RU", { maximumFractionDigits: 4 })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </main>
      )}

      {screen === "nfts" && (
        <NftScreen
          nfts={nfts}
          network={network}
          onSelect={(nft) => { setSelectedNft(nft); setScreen("nftDetail"); }}
          onBack={() => setScreen("home")}
        />
      )}

      {screen === "nftDetail" && selectedNft && (
        <NftDetailScreen
          nft={selectedNft}
          wallet={wallet}
          network={network}
          onBack={() => setScreen("nfts")}
          onDone={() => { setScreen("nfts"); void refresh(); }}
        />
      )}

      {screen === "send" && (
        <SendScreen
          wallet={wallet}
          onCancel={() => setScreen("home")}
          onSent={() => { setScreen("home"); void refresh(); }}
        />
      )}

      {screen === "receive" && (
        <ReceiveScreen wallet={wallet} onCancel={() => setScreen("home")} />
      )}

      {screen === "settings" && (
        <SettingsScreen
          wallet={wallet}
          network={network}
          linked={Boolean(linkAccount)}
          onNetworkChange={(n) => { setNetwork(n); setNet(n); }}
          onLogout={() => { forgetWallet(); setWallet(null); setOnboard("create"); }}
          onExport={() => setScreen("seed")}
          onLink={() => setScreen("link")}
          onBack={() => setScreen("home")}
        />
      )}

      {screen === "link" && wallet && (
        <LinkScreen
          wallet={wallet}
          network={network}
          account={linkAccount}
          onBack={() => setScreen("home")}
          onLinked={(account) => { setLinkAccount(account); setScreen("home"); }}
        />
      )}

      {screen === "seed" && (
        <SeedScreen wallet={wallet} onBack={() => setScreen("settings")} />
      )}
    </div>
  );
}

// ---------- Компоненты ----------

function ActionButton({ icon, label, onClick, badge }: { icon: React.ReactNode; label: string; onClick: () => void; badge?: number }) {
  return (
    <button className="action" onClick={onClick}>
      <span className="action-icon">
        {icon}
        {badge ? <span className="action-badge">{badge > 99 ? "99+" : badge}</span> : null}
      </span>
      <span>{label}</span>
    </button>
  );
}

// ---------- NFT ----------

function nftIcon(category: NftItem["category"], size = 15) {
  if (category === "username") return <AtSign size={size} />;
  if (category === "number") return <Hash size={size} />;
  if (category === "gift") return <GiftIcon size={size} />;
  return <ImageIcon size={size} />;
}

function NftThumb({ nft, size = 48 }: { nft: NftItem; size?: number }) {
  const [failed, setFailed] = useState(false);
  if (!nft.image || failed) {
    return (
      <div className="nft-thumb placeholder" style={{ width: size, height: size }}>
        {nftIcon(nft.category, size * 0.45)}
      </div>
    );
  }
  return (
    <img
      className="nft-thumb"
      src={nft.image}
      alt={nft.name}
      style={{ width: size, height: size }}
      onError={() => setFailed(true)}
      loading="lazy"
    />
  );
}

function NftScreen({ nfts, network, onSelect, onBack }: {
  nfts: NftItem[]; network: Network; onSelect: (n: NftItem) => void; onBack: () => void;
}) {
  const [tab, setTab] = useState<"all" | NftItem["category"]>("all");
  const visible = useMemo(
    () => (tab === "all" ? nfts : nfts.filter((n) => n.category === tab)),
    [nfts, tab]
  );
  const tabs: { key: "all" | NftItem["category"]; label: string; count: number }[] = [
    { key: "all", label: "Все", count: nfts.length },
    { key: "username", label: "Юзы", count: nfts.filter((n) => n.category === "username").length },
    { key: "number", label: "Номера", count: nfts.filter((n) => n.category === "number").length },
    { key: "gift", label: "Подарки", count: nfts.filter((n) => n.category === "gift").length },
    { key: "other", label: "Другое", count: nfts.filter((n) => n.category === "other").length },
  ];

  return (
    <div className="page">
      <div className="page-head">
        <button className="icon-btn" onClick={onBack}><X size={20} /></button>
        <h1>NFT</h1>
        <span className="net-pill">{network === "mainnet" ? "TON" : "testnet"}</span>
      </div>

      <div className="nft-tabs">
        {tabs.map((t) => (
          <button key={t.key} className={`nft-tab ${tab === t.key ? "active" : ""}`} onClick={() => setTab(t.key)}>
            {t.label}{t.count > 0 && <span className="nft-tab-count">{t.count}</span>}
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <div className="empty nft-empty">
          <ImageIcon size={36} />
          <strong>Пусто</strong>
          <span>NFT, привязанные к этому кошельку, появятся здесь: юзы, анонимные номера и NFT-подарки из Telegram.</span>
        </div>
      ) : (
        <div className="nft-grid">
          {visible.map((nft) => (
            <button className="nft-card" key={nft.address} onClick={() => onSelect(nft)}>
              <NftThumb nft={nft} size={64} />
              <div className="nft-card-body">
                <div className="nft-card-name">{nft.name || `#${nft.index}`}</div>
                <div className="nft-card-col">{nft.collectionName || "Без коллекции"}</div>
                {nft.onSale && <div className="nft-card-sale">на продаже · {nft.salePriceTon} TON</div>}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function NftDetailScreen({ nft, wallet, network, onBack, onDone }: {
  nft: NftItem; wallet: StoredWallet; network: Network; onBack: () => void; onDone: () => void;
}) {
  const [sending, setSending] = useState(false);
  const [to, setTo] = useState("");
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  async function transfer() {
    if (!to.trim()) { setError("Введите адрес получателя"); return; }
    setSending(true);
    setError("");
    setOk("");
    try {
      const msg = await sendNft({ mnemonic: wallet.mnemonic, nftAddress: nft.address, newOwner: to.trim() });
      setOk(msg);
      setTimeout(onDone, 2000);
    } catch (e: any) {
      setError(e.message || "Не удалось отправить NFT");
    } finally {
      setSending(false);
    }
  }

  const sell = sellUrl(nft, network);

  return (
    <div className="page">
      <div className="page-head">
        <button className="icon-btn" onClick={onBack}><X size={20} /></button>
        <h1>{nft.name || `NFT #${nft.index}`}</h1>
        <span className="net-pill">{network === "mainnet" ? "TON" : "testnet"}</span>
      </div>

      <div className="nft-detail-hero">
        <NftThumb nft={nft} size={132} />
      </div>

      <div className="kv-list">
        <div className="kv"><span>Коллекция</span><strong>{nft.collectionName || "—"}</strong></div>
        <div className="kv"><span>Тип</span><strong>{nft.category === "username" ? "Юзернейм" : nft.category === "number" ? "Номер" : nft.category === "gift" ? "Подарок" : "NFT"}</strong></div>
        {nft.onSale && <div className="kv"><span>Цена продажи</span><strong>{nft.salePriceTon} TON</strong></div>}
        <div className="kv"><span>Адрес NFT</span><code className="kv-mono">{shortAddress(nft.address)}</code></div>
        <div className="kv"><span>Владелец</span><code className="kv-mono">{nft.ownerAddress === wallet.address ? "вы" : shortAddress(nft.ownerAddress)}</code></div>
      </div>

      {nft.description && <p className="nft-desc">{nft.description}</p>}

      <div className="btn-col">
        <a className="btn" href={explorerUrl(nft.address, network)} target="_blank" rel="noreferrer">
          <ExternalLink size={17} /> Открыть в обозревателе
        </a>
        {sell && nft.verified && (
          <a className="btn" href={sell} target="_blank" rel="noreferrer">
            <ShoppingBag size={17} /> Продать на {nft.category === "gift" ? "Getgems" : "Fragment"}
          </a>
        )}
      </div>

      <label className="field">
        <span>Переслать на адрес</span>
        <input value={to} onChange={(e) => setTo(e.target.value)} placeholder="EQ… / UQ…" />
      </label>
      {error && <div className="alert">{error}</div>}
      {ok && <div className="ok">{ok}</div>}
      <button className="btn primary big" onClick={transfer} disabled={sending || !to.trim()}>
        <Send size={18} /> {sending ? "Отправляем…" : "Переслать NFT"}
      </button>
      <p className="hint">Пересылка доступна для любого NFT: юза, номера или подарка. Получатель станет новым владельцем в блокчейне.</p>
    </div>
  );
}

function Onboarding({ mode, onDone }: { mode: "create" | "import"; onDone: (w: StoredWallet) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<StoredWallet | null>(null);
  const [words, setWords] = useState<string[]>(Array(24).fill(""));

  async function doCreate() {
    setBusy(true);
    setError("");
    try {
      const w = await createWallet();
      setCreated(w);
    } catch (e: any) {
      setError(e.message || "Ошибка");
    } finally {
      setBusy(false);
    }
  }

  async function doImport() {
    setBusy(true);
    setError("");
    try {
      const filled = words.map((w) => w.trim()).filter(Boolean);
      if (filled.length < 12) throw new Error("Введите не менее 12 слов");
      const w = await importWallet(filled);
      onDone(w);
    } catch (e: any) {
      setError(e.message || "Ошибка");
    } finally {
      setBusy(false);
    }
  }

  if (mode === "create") {
    return (
      <div className="onboard-flow">
        {!created ? (
          <>
            <p className="hint">Создайте новый кошелёк. Seed-фраза из 24 слов позволит восстановить его в TON Keeper и других кошельках.</p>
            {error && <div className="alert">{error}</div>}
            <button className="btn primary big" onClick={doCreate} disabled={busy}>
              {busy ? "Создаём…" : "Создать кошелёк"}
            </button>
          </>
        ) : (
          <>
            <h3>Сохраните seed-фразу</h3>
            <div className="seed-grid">
              {created.mnemonic.map((w, i) => (
                <div className="seed-word" key={i}>
                  <span className="seed-idx">{i + 1}</span>{w}
                </div>
              ))}
            </div>
            <div className="warn">Никому не показывайте и не пересылайте эти слова. Узнав их, можно забрать все средства.</div>
            <button className="btn primary big" onClick={() => onDone(created)}>
              <Check size={18} /> Я сохранил
            </button>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="onboard-flow">
      <h3>Восстановление</h3>
      <p className="hint">Введите seed-фразу (12 или 24 слова через пробел).</p>
      <textarea
        className="seed-input"
        rows={4}
        placeholder="bakery marble wealth ..."
        value={words.join(" ")}
        onChange={(e) => setWords(e.target.value.split(/\s+/).slice(0, 24))}
      />
      {error && <div className="alert">{error}</div>}
      <button className="btn primary big" onClick={doImport} disabled={busy}>
        {busy ? "Восстанавливаем…" : "Восстановить кошелёк"}
      </button>
    </div>
  );
}

function SendScreen({ wallet, onCancel, onSent }: { wallet: StoredWallet; onCancel: () => void; onSent: () => void }) {
  const [to, setTo] = useState("");
  const [amount, setAmount] = useState("");
  const [comment, setComment] = useState("");
  const [fee, setFee] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        if (to.trim().length > 40 && Number(amount) > 0) {
          setFee(await estimateFee(to.trim(), amount, wallet.mnemonic));
        }
      } catch { /* ignore */ }
    }, 700);
    return () => clearTimeout(t);
  }, [to, amount, wallet.mnemonic]);

  async function submit() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const msg = await sendTon({ mnemonic: wallet.mnemonic, to: to.trim(), amountTon: amount, comment });
      setInfo(msg);
      setTimeout(onSent, 2500);
    } catch (e: any) {
      setError(e.message || "Не удалось отправить");
    } finally {
      setBusy(false);
    }
  }

  const valid = to.trim().length > 30 && Number(amount) > 0;

  return (
    <Modal title="Отправить" onClose={onCancel}>
      <label className="field">
        <span>Адрес получателя</span>
        <input value={to} onChange={(e) => setTo(e.target.value)} placeholder="EQ… / UQ…" />
      </label>
      <label className="field">
        <span>Сумма, TON</span>
        <div className="amount-input">
          <input value={amount} onChange={(e) => setAmount(e.target.value)} type="number" min="0" step="any" placeholder="0.0" />
          <span className="suffix">TON</span>
        </div>
      </label>
      <label className="field">
        <span>Комментарий (необязательно)</span>
        <input value={comment} onChange={(e) => setComment(e.target.value)} maxLength={120} />
      </label>
      <div className="fee-row">
        <span>Комиссия сети</span>
        <strong>{fee ? `~${fee} TON` : "—"}</strong>
      </div>
      {error && <div className="alert">{error}</div>}
      {info && <div className="ok">{info}</div>}
      <button className="btn primary big" onClick={submit} disabled={!valid || busy}>
        <Send size={18} /> {busy ? "Отправляем…" : "Отправить"}
      </button>
    </Modal>
  );
}

function ReceiveScreen({ wallet, onCancel }: { wallet: StoredWallet; onCancel: () => void }) {
  const [copied, setCopied] = useState(false);
  const link = `ton://transfer/${wallet.address}`;

  return (
    <Modal title="Получить" onClose={onCancel}>
      <div className="qr-box">
        <QrCode size={96} strokeWidth={1} />
        <div className="qr-hint">Покажите адрес отправителю</div>
      </div>
      <div className="addr-full">
        <code>{wallet.address}</code>
      </div>
      <div className="btn-row">
        <button className="btn" onClick={() => { navigator.clipboard.writeText(wallet.address); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>
          {copied ? <Check size={16} /> : <Copy size={16} />} {copied ? "Скопировано" : "Копировать"}
        </button>
        <a className="btn" href={link}><Link2 size={16} /> Открыть в кошельке</a>
      </div>
      <div className="topup">
        <div className="topup-title"><Coins size={16} /> Пополнить баланс</div>
        <a className="btn big" href="https://toncenter.com" target="_blank" rel="noreferrer">
          <ExternalLink size={17} /> Купить TON за рубли/крипту
        </a>
        <a className="btn big" href={`https://tonviewer.com/${wallet.address}`} target="_blank" rel="noreferrer">
          <ExternalLink size={17} /> Проверить поступление
        </a>
        <p className="hint">
          Пополнение — обычный перевод TON на адрес кошелька из любого обменника или другого кошелька.
          NFT (юзы, анонимные номера, подарки) Telegram приходят на этот же адрес сами — либо через
          Fragment/Getgems, либо переводом от другого кошелька.
        </p>
      </div>
    </Modal>
  );
}

function SettingsScreen({ wallet, network, linked, onNetworkChange, onLogout, onExport, onLink, onBack }: {
  wallet: StoredWallet; network: Network; linked: boolean; onNetworkChange: (n: Network) => void; onLogout: () => void; onExport: () => void; onLink: () => void; onBack: () => void;
}) {
  return (
    <Modal title="Настройки" onClose={onBack}>
      <div className="settings-row">
        <span>Сеть</span>
        <div className="net-switch">
          <button className={network === "mainnet" ? "active" : ""} onClick={() => onNetworkChange("mainnet")}>Mainnet</button>
          <button className={network === "testnet" ? "active" : ""} onClick={() => onNetworkChange("testnet")}>Testnet</button>
        </div>
      </div>
      <div className="settings-row">
        <span>Адрес</span>
        <code className="short">{shortAddress(wallet.address)}</code>
      </div>
      <button className="settings-row as-button" onClick={onLink}>
        <span>Аккаунт ShapitoGram</span>
        <span className={`settings-link-value ${linked ? "on" : ""}`}>
          {linked ? <BadgeCheck size={15} /> : <Phone size={15} />} {linked ? "привязан" : "привязать"}
        </span>
      </button>
      <button className="btn big" onClick={onExport}><KeyRound size={18} /> Показать seed-фразу</button>
      <button className="btn danger big" onClick={onLogout}><Trash2 size={18} /> Удалить кошелёк с устройства</button>
    </Modal>
  );
}

// ---------- Привязка аккаунта ----------

function LinkScreen({ wallet, network, account, onBack, onLinked }: {
  wallet: StoredWallet;
  network: Network;
  account: LinkedAccount | null;
  onBack: () => void;
  onLinked: (account: LinkedAccount) => void;
}) {
  const [step, setStep] = useState<"phone" | "code" | "done">(account ? "done" : "phone");
  const [phone, setPhone] = useState(account?.phone ?? "");
  const [code, setCode] = useState("");
  const [linked, setLinked] = useState<LinkedAccount | null>(account);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  async function request() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const result = await requestCode(phone.trim(), wallet.address);
      setStep("code");
      setInfo(`Код отправлен в Telegram (@shapitogrambot). Действует ${Math.max(1, Math.round(result.expiresIn / 60))} мин.`);
    } catch (e: any) {
      setError(e.message || "Не удалось отправить код");
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const result = await confirmCode(phone.trim(), code.trim());
      setLinked(result.account);
      setInfo("Аккаунт привязан!");
      setTimeout(() => onLinked(result.account), 1600);
    } catch (e: any) {
      setError(e.message || "Неверный код");
    } finally {
      setBusy(false);
    }
  }

  async function unlink() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      await unlinkAccount(linked?.phone ?? phone.trim(), wallet.address);
      setLinked(null);
      setStep("phone");
      setCode("");
      setInfo("Аккаунт отвязан от этого кошелька.");
    } catch (e: any) {
      setError(e.message || "Не удалось отвязать аккаунт");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <button className="icon-btn" onClick={onBack}><X size={20} /></button>
        <h1>Привязка аккаунта</h1>
        <span className="net-pill">{network === "mainnet" ? "TON" : "testnet"}</span>
      </div>

      {step === "done" && linked && (
        <>
          <div className="link-hero">
            <BadgeCheck size={44} />
            <strong>{accountTitle(linked)}</strong>
            <span>{linked.phone}</span>
          </div>
          <p className="hint">
            Кошелёк привязан к аккаунту ShapitoGram. Когда подарок из блокчейна окажется
            на этом адресе, в чате будет написано, какой аккаунт его сейчас носит.
          </p>
          {error && <div className="alert">{error}</div>}
          {info && <div className="ok">{info}</div>}
          <button className="btn danger big" onClick={unlink} disabled={busy}>
            <Trash2 size={18} /> {busy ? "Отвязываем…" : "Отвязать аккаунт"}
          </button>
        </>
      )}

      {step === "phone" && (
        <>
          <p className="hint">
            Введите номер телефона вашего аккаунта ShapitoGram. Мы пришлём код в Telegram
            (@shapitogrambot) — введите его здесь, и кошелёк будет привязан к аккаунту.
          </p>
          <label className="field">
            <span>Номер телефона</span>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+7 900 000-00-00"
              inputMode="tel"
              autoComplete="tel"
            />
          </label>
          {error && <div className="alert">{error}</div>}
          {info && <div className="ok">{info}</div>}
          <button
            className="btn primary big"
            onClick={request}
            disabled={busy || phone.replace(/\D/g, "").length < 10}
          >
            <Phone size={18} /> {busy ? "Отправляем…" : "Получить код"}
          </button>
        </>
      )}

      {step === "code" && (
        <>
          <p className="hint">
            Код отправлен в Telegram на номер {phone}. Введите 6 цифр из сообщения
            от @shapitogrambot.
          </p>
          <label className="field">
            <span>Код из Telegram</span>
            <input
              className="code-input"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="••••••"
              inputMode="numeric"
              autoComplete="one-time-code"
            />
          </label>
          {error && <div className="alert">{error}</div>}
          {info && <div className="ok">{info}</div>}
          <button className="btn primary big" onClick={confirm} disabled={busy || code.length !== 6}>
            <Check size={18} /> {busy ? "Проверяем…" : "Привязать"}
          </button>
          <button
            className="btn ghost big"
            onClick={() => { setStep("phone"); setCode(""); setError(""); setInfo(""); }}
          >
            Изменить номер
          </button>
        </>
      )}
    </div>
  );
}

function SeedScreen({ wallet, onBack }: { wallet: StoredWallet; onBack: () => void }) {
  return (
    <Modal title="Seed-фраза" onClose={onBack}>
      <div className="warn">Не показывайте эти слова никому.</div>
      <div className="seed-grid">
        {wallet.mnemonic.map((w, i) => (
          <div className="seed-word" key={i}><span className="seed-idx">{i + 1}</span>{w}</div>
        ))}
      </div>
      <button className="btn big" onClick={() => navigator.clipboard.writeText(wallet.mnemonic.join(" "))}>
        <Copy size={18} /> Скопировать всё
      </button>
    </Modal>
  );
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="modal-mask">
      <div className="modal">
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="icon-btn" onClick={onClose}><X size={20} /></button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
