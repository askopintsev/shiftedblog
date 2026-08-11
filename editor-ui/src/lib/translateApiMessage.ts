import { t, type MessageKey } from "@/i18n";

/** Known DRF / Django English messages → i18n keys. */
const MESSAGE_KEYS: Record<string, MessageKey> = {
  "This field is required.": "apiError.fieldRequired",
  "Authentication credentials were not provided.":
    "apiError.authCredentialsMissing",
};

export function translateApiMessage(message: string): string {
  const trimmed = message.trim();
  const key = MESSAGE_KEYS[trimmed];
  return key ? t(key) : message;
}
