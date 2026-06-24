function extensionFor(file: File): string {
  const match = file.name.match(/\.[^.]+$/);
  return match?.[0].toLowerCase() ?? "";
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
    throw new Error("Canvas is not available.");
  }
  ctx.drawImage(bitmap, 0, 0);
  bitmap.close();
  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, "image/jpeg", 0.92),
  );
  if (!blob) {
    throw new Error("Could not encode image.");
  }
  return new File([blob], jpegName(file), {
    type: "image/jpeg",
    lastModified: file.lastModified,
  });
}

export async function normalizeImageFileForUpload(file: File): Promise<File> {
  if (!(await shouldConvertToJpeg(file))) return file;
  return imageBitmapToJpegFile(file);
}
