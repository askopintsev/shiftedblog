import { useMemo, useRef } from "react";
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
import { apiUpload } from "@/api/client";
import { ckeditorConfig } from "./ckeditor.config";
import { EmojiPalette } from "./components/EmojiPalette";
import { BodyStatsBar } from "./components/BodyStatsBar";
import { useDefaultJustify } from "./hooks/useDefaultJustify";
import type { Editor, EditorConfig } from "ckeditor5";

interface PostBodyEditorProps {
  value: string;
  onChange: (html: string) => void;
  onStatsHtml?: (html: string) => void;
}

function CustomUploadAdapter(loader: { file: Promise<File | null> }) {
  return {
    upload: async () => {
      const file = await loader.file;
      if (!file) throw new Error("No file");
      const body = new FormData();
      body.append("upload", file);
      const data = await apiUpload<{ url: string }>("/media/upload/", body);
      return { default: data.url };
    },
    abort: () => {},
  };
}

export function PostBodyEditor({ value, onChange, onStatsHtml }: PostBodyEditorProps) {
  const editorRef = useRef<Editor | null>(null);
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
          Undo,
          Paragraph,
        ],
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

  return (
    <div className="post-body-editor mx-auto max-w-[700px] space-y-2">
      <BodyStatsBar html={value} onHtmlChange={onStatsHtml} />
      <div className="relative">
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
        <CKEditor
          editor={ClassicEditor}
          data={value}
          config={editorConfig}
          onReady={(editor: Editor) => {
            editorRef.current = editor;
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
          }}
          onChange={(_event, editor) => {
            onChange(editor.getData());
          }}
        />
      </div>
    </div>
  );
}
