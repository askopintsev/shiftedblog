import { PostBodyEditorMock } from "@/features/posts/body-editor/PostBodyEditorMock";

export function DesignPreviewPage() {
  return (
    <div className="p-6">
      <h1 className="mb-4 text-xl font-semibold">Post editor mock</h1>
      <PostBodyEditorMock />
    </div>
  );
}
