import type { Editor } from "ckeditor5";

const DEFAULT_ALIGN = "justify";

export function useDefaultJustify() {
  function applyDefaultAlignment(editor: Editor) {
    editor.model.change((writer) => {
      const root = editor.model.document.getRoot();
      if (!root) return;
      for (const item of editor.model.createRangeIn(root)) {
        if (item.type === "elementStart") {
          const el = item.item;
          if (el.is("element") && editor.model.schema.checkAttribute(el, "alignment")) {
            if (!el.hasAttribute("alignment")) {
              writer.setAttribute("alignment", DEFAULT_ALIGN, el);
            }
          }
        }
      }
    });
  }

  function attachJustify(editor: Editor) {
    applyDefaultAlignment(editor);
    editor.model.document.on("change:data", () => {
      applyDefaultAlignment(editor);
    });
  }

  return { attachJustify };
}
