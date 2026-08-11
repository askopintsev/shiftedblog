import { useRef, useState, type RefObject } from "react";
import { Images } from "lucide-react";
import type { Editor } from "ckeditor5";
import { useT } from "@/i18n";
import { insertGalleryMarker } from "../galleryMarkerPlugin";
import { EditorToolbarButton } from "./EditorToolbarButton";
import { FloatingEditorPopover } from "./FloatingEditorPopover";

interface GalleryInsertButtonProps {
  editorRef: RefObject<Editor | null>;
}

export function GalleryInsertButton({ editorRef }: GalleryInsertButtonProps) {
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);
  const [galleryKey, setGalleryKey] = useState("1");
  const t = useT();

  const insertGallery = () => {
    const editor = editorRef.current;
    if (!editor) return;
    const key = Number(galleryKey);
    if (!Number.isFinite(key) || key < 1) return;
    insertGalleryMarker(editor, key);
    setOpen(false);
  };

  return (
    <>
      <EditorToolbarButton
        ref={buttonRef}
        icon={<Images className="size-4 text-accent" strokeWidth={2} />}
        active={open}
        aria-expanded={open}
        aria-haspopup="dialog"
        title={t("editor.insertGallery")}
        onClick={() => setOpen((value) => !value)}
      >
        {t("editor.addGallery")}
      </EditorToolbarButton>
      <FloatingEditorPopover
        open={open}
        onClose={() => setOpen(false)}
        anchorRef={buttonRef}
        ariaLabel={t("editor.galleryInsert")}
        className="w-72 max-h-none overflow-visible p-4"
      >
        <div className="space-y-3">
          <div>
            <label
              htmlFor="gallery-key-input"
              className="block text-sm font-medium text-text-primary"
            >
              {t("editor.galleryNumber")}
            </label>
            <p className="mt-1 text-xs text-text-muted">
              {t("editor.galleryNumberHelp")}
            </p>
          </div>
          <input
            id="gallery-key-input"
            type="number"
            min={1}
            step={1}
            value={galleryKey}
            onChange={(event) => setGalleryKey(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                insertGallery();
              }
            }}
            className="w-full rounded-lg border border-border px-3 py-2 text-sm"
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="rounded-lg border border-border px-3 py-1.5 text-sm text-text-secondary hover:bg-surface-muted"
              onClick={() => setOpen(false)}
            >
              {t("common.cancel")}
            </button>
            <button
              type="button"
              className="rounded-lg bg-accent px-3 py-1.5 text-sm text-white hover:opacity-90"
              onClick={insertGallery}
            >
              {t("editor.insert")}
            </button>
          </div>
        </div>
      </FloatingEditorPopover>
    </>
  );
}
