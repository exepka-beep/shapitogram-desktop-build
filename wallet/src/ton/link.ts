// Привязка аккаунта ShapitoGram к кошельку по номеру телефона + коду.
// Бэкенд — бот @shapitogrambot ( routes /tonlink/* ), доступен через nginx
// на том же origin, поэтому CORS не нужен.

export interface LinkedAccount {
  phone: string;
  wallet: string;
  telegramId: number;
  serverUserId: number;
  username: string;
  firstName: string;
  linkedAt?: string;
}

export interface LinkStatus {
  linked: boolean;
  account?: LinkedAccount;
}

const BASE = "/tonlink";

async function parse(response: Response): Promise<any> {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data?.message || "Не удалось выполнить операцию. Попробуйте позже.");
  }
  return data;
}

export async function requestCode(phone: string, wallet: string): Promise<{ expiresIn: number }> {
  const response = await fetch(`${BASE}/request`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ phone, wallet }),
  });
  const data = await parse(response);
  return { expiresIn: Number(data.expiresIn) || 600 };
}

export async function confirmCode(phone: string, code: string): Promise<{ account: LinkedAccount }> {
  const response = await fetch(`${BASE}/confirm`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ phone, code }),
  });
  const data = await parse(response);
  return { account: data.account as LinkedAccount };
}

export async function linkStatus(wallet: string): Promise<LinkStatus> {
  const response = await fetch(`${BASE}/status?wallet=${encodeURIComponent(wallet)}`);
  const data = await parse(response);
  return data as LinkStatus;
}

export async function unlinkAccount(phone: string, wallet: string): Promise<void> {
  const response = await fetch(`${BASE}/unlink`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ phone, wallet }),
  });
  await parse(response);
}

export function accountTitle(account: LinkedAccount): string {
  if (account.firstName && account.username) return `${account.firstName} · @${account.username}`;
  if (account.username) return `@${account.username}`;
  if (account.firstName) return account.firstName;
  return account.phone;
}
