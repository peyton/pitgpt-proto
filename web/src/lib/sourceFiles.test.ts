import { describe, expect, it } from "vitest";
import { readSourceFile } from "./sourceFiles";

describe("readSourceFile", () => {
  it("reads large text sources without applying the old 12000 character limit", async () => {
    const content = "x".repeat(13_000);
    const file = new File([content], "article.md", { type: "text/markdown" });

    await expect(readSourceFile(file)).resolves.toBe(content);
  });
});
