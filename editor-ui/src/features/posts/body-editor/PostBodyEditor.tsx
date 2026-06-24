import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CKEditor } from "@ckeditor/ckeditor5-react";
import {
  Alignment,
  Autoformat,
  BalloonToolbar,
  BlockQuote,
  Bold,
  ClassicEditor,
  Code,
  CodeBlock,
  Essentials,
  FontBackgroundColor,
  FontColor,
  FontFamily,
  FontSize,
  GeneralHtmlSupport,
  Heading,
  Highlight,
  HorizontalLine,
  Image,
  ImageCaption,
  ImageResize,
  ImageStyle,
  ImageToolbar,
  ImageUpload,
  Indent,
  Italic,
  Link,
  List,
  MediaEmbed,
  Paragraph,
  RemoveFormat,
  SourceEditing,
  SpecialCharacters,
  SpecialCharactersEssentials,
  Strikethrough,
  Subscript,
  Superscript,
  Table,
  TableToolbar,
  TodoList,
  Underline,
  Undo,
} from "ckeditor5";
import "ckeditor5/ckeditor5.css";
import "./content-styles.css";
import { apiFetch, apiUpload } from "@/api/client";
import type { GalleryImage } from "@/api/types";
import { normalizeImageFileForUpload } from "@/lib/imageUpload";
import { mediaUrl } from "@/lib/mediaUrl";
import { ckeditorConfig } from "./ckeditor.config";
import { EmojiPalette } from "./components/EmojiPalette";
import { BodyStatsBar } from "./components/BodyStatsBar";
import {
  encodeGalleryMarkers,
  GalleryMarkerPlugin,
  insertGalleryMarker,
  refreshGalleryMarkers,
} from "./galleryMarkerPlugin";
import { useDefaultJustify } from "./hooks/useDefaultJustify";
import type { Editor, EditorConfig } from "ckeditor5";

interface PostBodyEditorProps {
  value: string;
  onChange: (html: string) => void;
  onStatsHtml?: (html: string) => void;
  galleryImages?: GalleryImage[];
  postId?: number;
  onGalleryUploaded?: () => void;
}

function CustomUploadAdapter(loader: { file: Promise<File | null> }) {
  return {
    upload: async () => {
      const file = await loader.file;
      if (!file) throw new Error("No file");
      const body = new FormData();
      body.append("upload", file);
      const data = await apiUpload<{ url: string }>("/media/upload/", body);
      return { default: mediaUrl(data.url) };
    },
    abort: () => {},
  };
}

function appendDroppedPreviews(marker: HTMLElement, files: File[]): () => void {
  marker.querySelector(".ck-gallery-marker__empty")?.remove();
  let grid = marker.querySelector<HTMLElement>(".ck-gallery-marker__grid");
  if (!grid) {
    grid = document.createElement("div");
    grid.className = "ck-gallery-marker__grid";
    marker.appendChild(grid);
  }

  const urls: string[] = [];
  const nodes: HTMLImageElement[] = [];
  for (const file of files) {
    const url = URL.createObjectURL(file);
    urls.push(url);
    const thumb = document.createElement("img");
    thumb.className = "ck-gallery-marker__thumb ck-gallery-marker__thumb--local";
    thumb.src = url;
    thumb.alt = file.name;
    grid.appendChild(thumb);
    nodes.push(thumb);
  }

  const revoke = () => urls.forEach((url) => URL.revokeObjectURL(url));
  window.setTimeout(revoke, 30_000);
  return () => {
    nodes.forEach((node) => node.remove());
    revoke();
  };
}

function showGalleryDropMessage(marker: HTMLElement, message: string): void {
  marker.querySelector(".ck-gallery-marker__message")?.remove();
  const node = document.createElement("div");
  node.className = "ck-gallery-marker__message";
  node.textContent = message;
  marker.appendChild(node);
  window.setTimeout(() => node.remove(), 4000);
}

function repaintGalleryWidgets(editor: Editor): void {
  editor.setData(encodeGalleryMarkers(editor.getData()));
}

export function PostBodyEditor({
  value,
  onChange,
  onStatsHtml,
  galleryImages = [],
  postId,
  onGalleryUploaded,
}: PostBodyEditorProps) {
  const editorRef = useRef<Editor | null>(null);
  const [localGalleryImages, setLocalGalleryImages] =
    useState<GalleryImage[]>(galleryImages);
  const [editorError, setEditorError] = useState<string | null>(null);
  const editorData = useMemo(() => encodeGalleryMarkers(value), [value]);
  const localGalleryImagesRef = useRef(localGalleryImages);
  localGalleryImagesRef.current = localGalleryImages;
  const galleryEditorKey = useMemo(
    () => localGalleryImages.map((image) => image.id).join(":"),
    [localGalleryImages],
  );
  const editorConfig = useMemo(
    () =>
      ({
        ...ckeditorConfig,
        plugins: [
          Essentials,
          Autoformat,
          BalloonToolbar,
          Heading,
          Bold,
          Italic,
          Underline,
          Strikethrough,
          Code,
          Subscript,
          Superscript,
          SpecialCharacters,
          SpecialCharactersEssentials,
          Highlight,
          RemoveFormat,
          List,
          TodoList,
          BlockQuote,
          CodeBlock,
          Alignment,
          Indent,
          Image,
          ImageCaption,
          ImageResize,
          ImageStyle,
          ImageToolbar,
          ImageUpload,
          Link,
          FontSize,
          FontFamily,
          FontColor,
          FontBackgroundColor,
          MediaEmbed,
          Table,
          TableToolbar,
          HorizontalLine,
          SourceEditing,
          GeneralHtmlSupport,
          GalleryMarkerPlugin,
          Undo,
          Paragraph,
        ],
        galleryMarker: {
          getImages: () => localGalleryImagesRef.current,
        },
        balloonToolbar: ["bold", "italic", "link", "highlight"],
        image: {
          toolbar: [
            "imageStyle:full",
            "imageStyle:side",
            "imageStyle:alignLeft",
            "imageStyle:alignCenter",
            "imageStyle:alignRight",
            "toggleImageCaption",
            "imageTextAlternative",
          ],
        },
        table: {
          contentToolbar: [
            "tableColumn",
            "tableRow",
            "mergeTableCells",
            "tableProperties",
            "tableCellProperties",
          ],
        },
      }) as EditorConfig,
    [],
  );

  const { attachJustify } = useDefaultJustify();

  useEffect(() => {
    setLocalGalleryImages(galleryImages);
    localGalleryImagesRef.current = galleryImages;
    const editor = editorRef.current;
    if (editor) {
      repaintGalleryWidgets(editor);
      refreshGalleryMarkers(editor, galleryImages);
    }
  }, [galleryImages]);

  const uploadGalleryFiles = useCallback(
    async (galleryKey: number, files: File[]) => {
      if (!postId || !files.length) return;
      const uploaded: GalleryImage[] = [];
      for (const file of files) {
        const uploadFile = await normalizeImageFileForUpload(file);
        const fd = new FormData();
        fd.append("image", uploadFile);
        fd.append("gallery_key", String(galleryKey));
        const data = await apiUpload<{ ok: boolean; gallery: GalleryImage }>(
          `/posts/${postId}/gallery/`,
          fd,
        );
        uploaded.push(data.gallery);
      }
      const refreshed = await apiFetch<{ ok: boolean; results: GalleryImage[] }>(
        `/posts/${postId}/gallery/`,
      );
      const nextImages = refreshed.results.length
        ? refreshed.results
        : [...localGalleryImagesRef.current, ...uploaded];
      localGalleryImagesRef.current = nextImages;
      setLocalGalleryImages(nextImages);
      const editor = editorRef.current;
      if (editor) {
        repaintGalleryWidgets(editor);
        refreshGalleryMarkers(editor, nextImages);
        [0, 100, 500, 1500].forEach((delay) => {
          window.setTimeout(() => refreshGalleryMarkers(editor, nextImages), delay);
        });
      }
      onGalleryUploaded?.();
    },
    [onGalleryUploaded, postId],
  );

  const refreshGalleryImages = useCallback(async () => {
    if (!postId) return localGalleryImagesRef.current;
    const refreshed = await apiFetch<{ ok: boolean; results: GalleryImage[] }>(
      `/posts/${postId}/gallery/`,
    );
    const nextImages = refreshed.results;
    localGalleryImagesRef.current = nextImages;
    setLocalGalleryImages(nextImages);
    const editor = editorRef.current;
    if (editor) {
      repaintGalleryWidgets(editor);
      refreshGalleryMarkers(editor, nextImages);
    }
    onGalleryUploaded?.();
    return nextImages;
  }, [onGalleryUploaded, postId]);

  const deleteGalleryImage = useCallback(
    async (imageId: number) => {
      if (!postId || !imageId) return;
      await apiFetch(`/posts/${postId}/gallery/${imageId}/`, {
        method: "DELETE",
      });
      await refreshGalleryImages();
    },
    [postId, refreshGalleryImages],
  );

  const attachGalleryDropHandlers = useCallback(
    (editor: Editor) => {
      const editable = (
        editor.ui.view as unknown as { editable?: { element?: HTMLElement } }
      ).editable?.element;
      if (!editable) return () => {};

      const markerFromEvent = (event: DragEvent) => {
        const target = event.target;
        if (!(target instanceof Element)) return null;
        return target.closest<HTMLElement>(".ck-gallery-marker");
      };

      const claimGalleryDropEvent = (event: DragEvent) => {
        const marker = markerFromEvent(event);
        if (!marker) return null;
        event.preventDefault();
        event.stopPropagation();
        return marker;
      };

      const onDragEnter = (event: DragEvent) => {
        const marker = claimGalleryDropEvent(event);
        if (!marker) return;
        marker.classList.add("ck-gallery-marker--dragover");
      };

      const onDragOver = (event: DragEvent) => {
        const marker = claimGalleryDropEvent(event);
        if (!marker) return;
        if (event.dataTransfer) {
          event.dataTransfer.dropEffect = postId ? "copy" : "none";
        }
        marker.classList.add("ck-gallery-marker--dragover");
      };

      const onDragLeave = (event: DragEvent) => {
        const marker = markerFromEvent(event);
        marker?.classList.remove("ck-gallery-marker--dragover");
      };

      const onDrop = (event: DragEvent) => {
        const marker = claimGalleryDropEvent(event);
        if (!marker) return;
        marker.classList.remove("ck-gallery-marker--dragover");
        const droppedFiles = Array.from(event.dataTransfer?.files ?? []);
        const files = droppedFiles.filter(
          (file) => file.size > 0 && file.type.startsWith("image/"),
        );
        if (!files.length) {
          showGalleryDropMessage(marker, "Перетащите сюда файл изображения.");
          return;
        }
        const galleryKey = Number(marker.dataset.galleryKey) || 1;
        let removeDroppedPreviews = () => {};
        const previewTimer = window.setTimeout(() => {
          const liveMarker =
            editable.querySelector<HTMLElement>(
              `.ck-gallery-marker[data-gallery-key="${galleryKey}"]`,
            ) ?? marker;
          removeDroppedPreviews = appendDroppedPreviews(liveMarker, files);
        }, 50);
        marker.classList.add("ck-gallery-marker--uploading");
        void uploadGalleryFiles(galleryKey, files).catch(() => {
          window.clearTimeout(previewTimer);
          removeDroppedPreviews();
          marker.classList.add("ck-gallery-marker--error");
          window.setTimeout(
            () => marker.classList.remove("ck-gallery-marker--error"),
            1600,
          );
          showGalleryDropMessage(marker, "Не удалось загрузить изображение.");
        }).finally(() => {
          marker.classList.remove("ck-gallery-marker--uploading");
        });
      };

      const onClick = (event: MouseEvent) => {
        const target = event.target;
        if (!(target instanceof Element)) return;
        const button = target.closest<HTMLButtonElement>(
          ".ck-gallery-marker__delete",
        );
        if (!button) return;
        event.preventDefault();
        event.stopPropagation();
        const imageId = Number(button.dataset.galleryImageId);
        if (!imageId) return;
        if (!window.confirm("Удалить изображение из галереи?")) return;
        button.disabled = true;
        void deleteGalleryImage(imageId).catch(() => {
          button.disabled = false;
          const marker = button.closest<HTMLElement>(".ck-gallery-marker");
          if (marker) {
            showGalleryDropMessage(marker, "Не удалось удалить изображение.");
          }
        });
      };

      editable.addEventListener("click", onClick, true);
      editable.addEventListener("dragenter", onDragEnter, true);
      editable.addEventListener("dragover", onDragOver, true);
      editable.addEventListener("dragleave", onDragLeave, true);
      editable.addEventListener("drop", onDrop, true);

      return () => {
        editable.removeEventListener("click", onClick, true);
        editable.removeEventListener("dragenter", onDragEnter, true);
        editable.removeEventListener("dragover", onDragOver, true);
        editable.removeEventListener("dragleave", onDragLeave, true);
        editable.removeEventListener("drop", onDrop, true);
      };
    },
    [deleteGalleryImage, postId, uploadGalleryFiles],
  );

  return (
    <div className="post-body-editor mx-auto w-full max-w-[760px] space-y-3">
      <BodyStatsBar html={value} onHtmlChange={onStatsHtml} />
      <div className="post-body-editor-shell overflow-hidden rounded-xl border border-border bg-surface shadow-sm">
        <div className="flex items-center justify-end gap-2 border-b border-border bg-surface-muted px-3 py-2">
          <button
            type="button"
            className="inline-flex h-9 items-center rounded-lg border border-border bg-surface px-3 text-sm"
            onClick={() => {
              const editor = editorRef.current;
              if (!editor) return;
              const raw = window.prompt("Номер галереи", "1");
              if (raw === null) return;
              insertGalleryMarker(editor, Number(raw));
            }}
          >
            Добавить галерею
          </button>
          <EmojiPalette
            onInsert={(_editor, text) => {
              const editor = editorRef.current;
              if (!editor) return;
              editor.model.change((writer) => {
                const pos = editor.model.document.selection.getFirstPosition();
                if (pos) {
                  writer.insertText(text, pos);
                }
              });
              editor.editing.view.focus();
            }}
          />
        </div>
        {editorError ? (
          <div className="px-4 py-8 text-sm text-red-600">{editorError}</div>
        ) : (
          <CKEditor
            key={galleryEditorKey}
            editor={ClassicEditor}
            data={editorData}
            config={editorConfig}
            onReady={(editor: Editor) => {
              editorRef.current = editor;
              setEditorError(null);
              attachJustify(editor);
              editor.editing.view.change((writer) => {
                const root = editor.editing.view.document.getRoot();
                if (root) {
                  writer.setAttribute("spellcheck", "true", root);
                  writer.setAttribute("lang", "ru", root);
                }
              });
              editor.plugins.get("FileRepository").createUploadAdapter = (
                loader: { file: Promise<File | null> },
              ) => CustomUploadAdapter(loader);
              attachGalleryDropHandlers(editor);
            }}
            onChange={(_event, editor) => {
              onChange(editor.getData());
            }}
            onError={(error) => {
              setEditorError(
                error instanceof Error ? error.message : "Не удалось загрузить редактор.",
              );
            }}
          />
        )}
      </div>
    </div>
  );
}
