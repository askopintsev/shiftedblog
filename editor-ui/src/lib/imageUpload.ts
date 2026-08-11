import { t } from "@/i18n";

const EXT_BY_MIME: Record<string, string> = {
  "image/png": ".png",
  "image/jpeg": ".jpg",
  "image/jpg": ".jpg",
  "image/gif": ".gif",
  "image/webp": ".webp",
  "image/bmp": ".bmp",
  "image/tiff": ".tiff",
  "image/tif": ".tiff",
};

function extensionFor(file: File): string {
  const match = file.name.match(/\.[^.]+$/);
  return match?.[0].toLowerCase() ?? "";
}

/** Clipboard pastes often have an empty name or no extension — fix before upload. */
export function ensureImageFileName(file: File): File {
  const ext = extensionFor(file);
  if (file.name.trim() && ext) {
    return file;
  }
  const inferred =
    EXT_BY_MIME[file.type] || (file.type.startsWith("image/") ? ".png" : "");
  if (!inferred) {
    return file;
  }
  const stem =
    file.name.replace(/\.[^.]+$/, "").trim() ||
    `clipboard-image-${Date.now()}`;
  return new File([file], `${stem}${inferred}`, {
    type: file.type || "image/png",
    lastModified: file.lastModified || Date.now(),
  });
}

function jpegName(file: File): string {
  return file.name.replace(/\.[^.]+$/, "") + ".jpg";
}

async function hasWebpHeader(file: File): Promise<boolean> {
  const header = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  const riff = String.fromCharCode(...header.slice(0, 4));
  const webp = String.fromCharCode(...header.slice(8, 12));
  return riff === "RIFF" && webp === "WEBP";
}

async function shouldConvertToJpeg(file: File): Promise<boolean> {
  return (
    file.type === "image/webp" ||
    extensionFor(file) === ".webp" ||
    (await hasWebpHeader(file))
  );
}

async function imageBitmapToJpegFile(file: File): Promise<File> {
  const bitmap = await createImageBitmap(file);
  const canvas = document.createElement("canvas");
  canvas.width = bitmap.width;
  canvas.height = bitmap.height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    bitmap.close();
    throw new Error(t("image.canvasUnavailable"));
  }
  ctx.drawImage(bitmap, 0, 0);
  bitmap.close();
  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, "image/jpeg", 0.92),
  );
  if (!blob) {
    throw new Error(t("image.encodeFailed"));
  }
  return new File([blob], jpegName(file), {
    type: "image/jpeg",
    lastModified: file.lastModified,
  });
}

export async function normalizeImageFileForUpload(file: File): Promise<File> {
  const named = ensureImageFileName(file);
  if (!(await shouldConvertToJpeg(named))) return named;
  return imageBitmapToJpegFile(named);
}
