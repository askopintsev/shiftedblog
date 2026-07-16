import { Plugin, Widget, toWidget } from "ckeditor5";
import type { Editor } from "ckeditor5";
import type { GalleryImage } from "@/api/types";
import { mediaUrl } from "@/lib/mediaUrl";

export const GALLERY_MARKER_TAG = "section";
export const GALLERY_MARKER_ATTR = "data-gallery-marker";

export function encodeGalleryMarkers(html: string): string {
  return html.replace(
    /(?:<p>\s*)?\[gallery:(\d+)\](?:\s*<\/p>)?/gi,
    (_match, key: string) =>
      `<${GALLERY_MARKER_TAG} ${GALLERY_MARKER_ATTR}="${key}"></${GALLERY_MARKER_TAG}>`,
  );
}

interface GalleryMarkerConfig {
  images?: GalleryImage[];
  getImages?: () => GalleryImage[];
}

function galleryImagesByKey(images: GalleryImage[] = []): Map<number, GalleryImage[]> {
  const grouped = new Map<number, GalleryImage[]>();
  for (const image of images) {
    const current = grouped.get(image.gallery_key) ?? [];
    current.push(image);
    grouped.set(image.gallery_key, current);
  }
  for (const group of grouped.values()) {
    group.sort((a, b) => a.order - b.order || a.id - b.id);
  }
  return grouped;
}

function configFor(editor: Editor): GalleryMarkerConfig {
  return (editor.config.get("galleryMarker") ?? {}) as GalleryMarkerConfig;
}

function imagesFor(editor: Editor): GalleryImage[] {
  const config = configFor(editor);
  return config.getImages?.() ?? config.images ?? [];
}

function renderGalleryDom(marker: HTMLElement, images: GalleryImage[]): void {
  const key = Number(marker.dataset.galleryKey) || 1;
  marker.querySelector(".ck-gallery-marker__grid")?.remove();
  marker.querySelector(".ck-gallery-marker__empty")?.remove();

  if (images.length) {
    const grid = document.createElement("div");
    grid.className = "ck-gallery-marker__grid";
    for (const image of images) {
      const item = document.createElement("figure");
      item.className = "ck-gallery-marker__item";
      item.dataset.galleryImageId = String(image.id);
      const thumb = document.createElement("img");
      thumb.className = "ck-gallery-marker__thumb";
      thumb.src = mediaUrl(image.image_url);
      thumb.alt = image.caption || `Gallery ${key}`;
      item.appendChild(thumb);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "ck-gallery-marker__delete";
      remove.dataset.galleryImageId = String(image.id);
      remove.setAttribute("aria-label", "Удалить изображение из галереи");
      remove.textContent = "×";
      item.appendChild(remove);
      grid.appendChild(item);
    }
    marker.appendChild(grid);
    return;
  }

  const empty = document.createElement("div");
  empty.className = "ck-gallery-marker__empty";
  empty.textContent = "Перетащите изображения сюда или добавьте их на вкладке Галерея.";
  marker.appendChild(empty);
}

export function refreshGalleryMarkers(editor: Editor, images: GalleryImage[]): void {
  const editable = (
    editor.ui.view as unknown as { editable?: { element?: HTMLElement } }
  ).editable?.element;
  if (!editable) return;
  const grouped = galleryImagesByKey(images);
  editable.querySelectorAll<HTMLElement>(".ck-gallery-marker").forEach((marker) => {
    const key = Number(marker.dataset.galleryKey) || 1;
    renderGalleryDom(marker, grouped.get(key) ?? []);
  });
}

export class GalleryMarkerPlugin extends Plugin {
  static get requires() {
    return [Widget];
  }

  init() {
    const { editor } = this;

    editor.model.schema.register("galleryMarker", {
      inheritAllFrom: "$blockObject",
      allowAttributes: ["galleryKey"],
    });

    editor.conversion.for("upcast").elementToElement({
      view: {
        name: GALLERY_MARKER_TAG,
        attributes: {
          [GALLERY_MARKER_ATTR]: true,
        },
      },
      model: (viewElement, { writer }) => {
        const key = Number(viewElement.getAttribute(GALLERY_MARKER_ATTR)) || 1;
        return writer.createElement("galleryMarker", { galleryKey: key });
      },
    });

    editor.conversion.for("dataDowncast").elementToElement({
      model: "galleryMarker",
      view: (modelElement, { writer }) => {
        const key = Number(modelElement.getAttribute("galleryKey")) || 1;
        const paragraph = writer.createContainerElement("p");
        writer.insert(
          writer.createPositionAt(paragraph, 0),
          writer.createText(`[gallery:${key}]`),
        );
        return paragraph;
      },
    });

    editor.conversion.for("editingDowncast").elementToElement({
      model: "galleryMarker",
      view: (modelElement, { writer }) => {
        const key = Number(modelElement.getAttribute("galleryKey")) || 1;
        const grouped = galleryImagesByKey(imagesFor(editor));
        const images = grouped.get(key) ?? [];
        const wrapper = writer.createContainerElement("section", {
          class: "ck-gallery-marker",
          "data-gallery-key": String(key),
        });
        const title = writer.createContainerElement("div", {
          class: "ck-gallery-marker__title",
        });
        writer.insert(
          writer.createPositionAt(title, 0),
          writer.createText(`Галерея ${key}`),
        );
        writer.insert(writer.createPositionAt(wrapper, 0), title);

        const marker = writer.createContainerElement("div", {
          class: "ck-gallery-marker__code",
        });
        writer.insert(
          writer.createPositionAt(marker, 0),
          writer.createText(`[gallery:${key}]`),
        );
        writer.insert(writer.createPositionAt(wrapper, "end"), marker);

        if (images.length) {
          const grid = writer.createContainerElement("div", {
            class: "ck-gallery-marker__grid",
          });
          for (const image of images) {
            const item = writer.createContainerElement("figure", {
              class: "ck-gallery-marker__item",
              "data-gallery-image-id": String(image.id),
            });
            const thumb = writer.createEmptyElement("img", {
              class: "ck-gallery-marker__thumb",
              src: mediaUrl(image.image_url),
              alt: image.caption || `Gallery ${key}`,
            });
            writer.insert(writer.createPositionAt(item, "end"), thumb);
            const remove = writer.createContainerElement("button", {
              type: "button",
              class: "ck-gallery-marker__delete",
              "data-gallery-image-id": String(image.id),
              "aria-label": "Удалить изображение из галереи",
            });
            writer.insert(writer.createPositionAt(remove, 0), writer.createText("×"));
            writer.insert(writer.createPositionAt(item, "end"), remove);
            writer.insert(writer.createPositionAt(grid, "end"), item);
          }
          writer.insert(writer.createPositionAt(wrapper, "end"), grid);
        } else {
          const empty = writer.createContainerElement("div", {
            class: "ck-gallery-marker__empty",
          });
          writer.insert(
            writer.createPositionAt(empty, 0),
            writer.createText(
              "Перетащите изображения сюда или добавьте их на вкладке Галерея.",
            ),
          );
          writer.insert(writer.createPositionAt(wrapper, "end"), empty);
        }

        return toWidget(wrapper, writer, { label: `Галерея ${key}` });
      },
    });
  }
}

export function insertGalleryMarker(editor: Editor, key: number): void {
  editor.model.change((writer) => {
    const gallery = writer.createElement("galleryMarker", {
      galleryKey: Math.max(1, Math.floor(key) || 1),
    });
    editor.model.insertObject(gallery, null, null, { setSelection: "on" });
  });
  editor.editing.view.focus();
}
