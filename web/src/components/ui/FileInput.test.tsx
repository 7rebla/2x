import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { type ReactElement, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../../i18n.ts";
import { fileButtonClasses, fileDropClasses } from "./classes.ts";
import { FileInput } from "./FileInput.tsx";

afterEach(async () => {
  cleanup();
  vi.restoreAllMocks();
  await changeLanguage("en");
});

function testFile(name = "test-manual.pdf"): File {
  return new File(["test content"], name, { type: "application/pdf" });
}

/** A labelled chooser that keeps its file like the pages do. */
function Chooser({
  onFile = () => undefined,
  disabled = false,
  invalid = false,
}: {
  onFile?: (file: File | null) => void;
  disabled?: boolean;
  invalid?: boolean;
}): ReactElement {
  const [file, setFile] = useState<File | null>(null);
  return (
    <>
      <label htmlFor="test-file">File</label>
      <FileInput
        id="test-file"
        name="file"
        accept=".pdf"
        data-testid="test-file-input"
        file={file}
        disabled={disabled}
        invalid={invalid}
        aria-describedby="test-hint"
        onFileChange={(next) => {
          setFile(next);
          onFile(next);
        }}
      />
      <p id="test-hint">Test hint</p>
    </>
  );
}

function frame(): HTMLElement {
  const parent = screen.getByLabelText("File").parentElement;
  if (parent === null) {
    throw new Error("no frame");
  }
  return parent;
}

describe("FileInput", () => {
  it("keeps the native input, named by the caller's label, visually hidden", () => {
    render(<Chooser />);
    const input = screen.getByLabelText<HTMLInputElement>("File");
    expect(input.tagName).toBe("INPUT");
    expect(input.type).toBe("file");
    expect(input.name).toBe("file");
    expect(input.accept).toBe(".pdf");
    expect(input.dataset.testid).toBe("test-file-input");
    expect(input.getAttribute("aria-describedby")).toBe("test-hint");
    expect(input.className).toContain("sr-only");
    expect(input.className).toContain("peer");
    expect(input.getAttribute("aria-invalid")).toBe("false");
    // Still focusable: keyboard users reach the chooser through the input.
    input.focus();
    expect(document.activeElement).toBe(input);
  });

  it("shows a secondary button, no file yet and the drop hint", () => {
    render(<Chooser />);
    const visibleButton = screen.getByText("Choose file…");
    expect(visibleButton.getAttribute("aria-hidden")).toBe("true");
    expect(visibleButton.className).toBe(fileButtonClasses());
    expect(visibleButton.className).toContain("min-h-9");
    expect(visibleButton.className).toContain("peer-focus-visible:outline-focus");
    expect(visibleButton.querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
    expect(screen.getByTestId("file-input-name").textContent).toBe("No file chosen");
    expect(screen.getByText("or drop it here")).toBeDefined();
    expect(frame().className).toBe(fileDropClasses(false));
    expect(frame().className).toContain("border-dashed");
  });

  it("opens the native chooser when the visible button is clicked", () => {
    const click = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => undefined);
    render(<Chooser />);
    fireEvent.click(screen.getByText("Choose file…"));
    expect(click).toHaveBeenCalledTimes(1);
  });

  it("reports a chosen file and shows its name", () => {
    const onFile = vi.fn();
    render(<Chooser onFile={onFile} />);
    const file = testFile();
    fireEvent.change(screen.getByLabelText("File"), { target: { files: [file] } });
    expect(onFile).toHaveBeenCalledWith(file);
    const name = screen.getByTestId("file-input-name");
    expect(name.textContent).toBe("test-manual.pdf");
    expect(name.getAttribute("title")).toBe("test-manual.pdf");

    fireEvent.change(screen.getByLabelText("File"), { target: { files: [] } });
    expect(onFile).toHaveBeenLastCalledWith(null);
    expect(screen.getByTestId("file-input-name").textContent).toBe("No file chosen");
  });

  it("takes the first dropped file and marks the frame while dragging", () => {
    const onFile = vi.fn();
    render(<Chooser onFile={onFile} />);
    const zone = frame();

    fireEvent.dragOver(zone);
    expect(zone.dataset.dragging).toBe("true");
    expect(zone.className).toBe(fileDropClasses(true));
    expect(zone.className).toContain("bg-accent-soft");
    fireEvent.dragLeave(zone);
    expect(zone.dataset.dragging).toBeUndefined();

    const first = testFile("first.pdf");
    fireEvent.dragOver(zone);
    fireEvent.drop(zone, { dataTransfer: { files: [first, testFile("second.pdf")] } });
    expect(onFile).toHaveBeenCalledTimes(1);
    expect(onFile).toHaveBeenCalledWith(first);
    expect(zone.dataset.dragging).toBeUndefined();
    expect(screen.getByTestId("file-input-name").textContent).toBe("first.pdf");
  });

  it("ignores a drop without files", () => {
    const onFile = vi.fn();
    render(<Chooser onFile={onFile} />);
    fireEvent.drop(frame(), { dataTransfer: { files: [] } });
    expect(onFile).not.toHaveBeenCalled();
  });

  it("does nothing while disabled", () => {
    const onFile = vi.fn();
    const click = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => undefined);
    render(<Chooser onFile={onFile} disabled />);
    expect(screen.getByLabelText<HTMLInputElement>("File").disabled).toBe(true);
    expect(screen.getByText("Choose file…").className).toContain("peer-disabled:opacity-50");
    expect(screen.queryByText("or drop it here")).toBeNull();

    fireEvent.click(screen.getByText("Choose file…"));
    fireEvent.dragOver(frame());
    fireEvent.drop(frame(), { dataTransfer: { files: [testFile()] } });
    expect(click).not.toHaveBeenCalled();
    expect(onFile).not.toHaveBeenCalled();
    expect(frame().dataset.dragging).toBeUndefined();
  });

  it("marks an error at the input, which colours the frame", () => {
    render(<Chooser invalid />);
    expect(screen.getByLabelText("File").getAttribute("aria-invalid")).toBe("true");
    expect(frame().className).toContain("has-[input[aria-invalid=true]]:border-danger");
  });

  it("speaks German", async () => {
    await changeLanguage("de");
    render(<Chooser />);
    expect(screen.getByText("Datei wählen …")).toBeDefined();
    expect(screen.getByTestId("file-input-name").textContent).toBe("Keine Datei gewählt");
    expect(screen.getByText("oder hier ablegen")).toBeDefined();
  });
});
