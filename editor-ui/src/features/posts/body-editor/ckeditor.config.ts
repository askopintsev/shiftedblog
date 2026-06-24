/**
 * Mirrors shiftedblog/settings.py CKEDITOR_5_CONFIGS["default"].
 * Keep in sync when Django toolbar changes.
 */

export const ckeditorToolbarItems = [
  "heading",
  "|",
  "bold",
  "italic",
  "underline",
  "strikethrough",
  "code",
  "subscript",
  "superscript",
  "specialCharacters",
  "highlight",
  "removeFormat",
  "|",
  "numberedList",
  "bulletedList",
  "todoList",
  "|",
  "blockQuote",
  "|",
  "codeBlock",
  "|",
  "alignment",
  "outdent",
  "indent",
  "|",
  "uploadImage",
  "|",
  "link",
  "unlink",
  "|",
  "fontSize",
  "fontFamily",
  "fontColor",
  "fontBackgroundColor",
  "|",
  "mediaEmbed",
  "insertTable",
  "horizontalLine",
  "sourceEditing",
  "|",
  "undo",
  "redo",
];

export const ckeditorConfig = {
  toolbar: {
    items: ckeditorToolbarItems,
    shouldNotGroupWhenFull: true,
  },
  language: "ru",
  placeholder: "Начните писать…",
  alignment: {
    options: ["left", "right", "center", "justify"],
  },
  fontFamily: {
    options: [
      "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
      "default",
      "Arial, Helvetica, sans-serif",
      "Georgia, serif",
      "Times New Roman, Times, serif",
      "Verdana, Geneva, sans-serif",
    ],
  },
  fontSize: {
    options: [18, "default", "tiny", "small", "big", "huge"],
  },
};
