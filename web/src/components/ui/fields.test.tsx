import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { createRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { buttonClasses, CONTROL_HEIGHT_PX, fieldClasses, textareaClasses } from "./classes.ts";
import { Input, Select, Textarea } from "./fields.tsx";

afterEach(() => {
  cleanup();
});

describe("Input", () => {
  it("is a labelled text field of height md by default", () => {
    render(
      <label>
        Name
        <Input defaultValue="Test site" />
      </label>,
    );
    const input = screen.getByRole("textbox", { name: "Name" });
    expect(input.getAttribute("type")).toBe("text");
    expect(input.className).toBe(fieldClasses("md"));
    expect(input.className).toContain("h-9");
    expect(input.getAttribute("aria-invalid")).toBeNull();
  });

  it("has size sm and keeps layout classes of the caller", () => {
    render(<Input aria-label="Filter" size="sm" className="w-72" />);
    const input = screen.getByRole("textbox", { name: "Filter" });
    expect(input.className).toBe(fieldClasses("sm", "w-72"));
    expect(input.className).toContain("h-7");
    // The native size attribute is replaced by the control size.
    expect(input.getAttribute("size")).toBeNull();
  });

  it("marks an error with aria-invalid and its description", () => {
    render(
      <>
        <Input aria-label="Key" invalid aria-describedby="key-error" />
        <p id="key-error">Key already exists.</p>
      </>,
    );
    const input = screen.getByRole("textbox", { name: "Key" });
    expect(input.getAttribute("aria-invalid")).toBe("true");
    expect(input.getAttribute("aria-describedby")).toBe("key-error");
    expect(input.className).toContain("aria-[invalid=true]:border-danger");
  });

  it("writes aria-invalid=false for a field that was checked and is fine", () => {
    render(<Input aria-label="Key" invalid={false} />);
    expect(screen.getByRole("textbox", { name: "Key" }).getAttribute("aria-invalid")).toBe("false");
  });

  it("supports search and password fields, change events and a ref", () => {
    const onChange = vi.fn();
    const ref = createRef<HTMLInputElement>();
    render(
      <>
        <Input aria-label="Search" type="search" onChange={onChange} />
        <Input ref={ref} aria-label="Password" type="password" />
      </>,
    );
    const search = screen.getByRole("searchbox", { name: "Search" });
    fireEvent.change(search, { target: { value: "192.0.2.10" } });
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(ref.current?.getAttribute("type")).toBe("password");
  });

  it("accepts only text-like types", () => {
    // @ts-expect-error -- check boxes keep the native input
    render(<Input type="checkbox" />);
  });

  it("looks disabled like every control", () => {
    render(<Input aria-label="Name" disabled />);
    const input = screen.getByRole("textbox", { name: "Name" });
    expect((input as HTMLInputElement).disabled).toBe(true);
    expect(input.className).toContain("disabled:opacity-50");
    expect(input.className).toContain("disabled:cursor-not-allowed");
  });
});

describe("Select", () => {
  it("is a labelled choice with the height of an md button", () => {
    const onChange = vi.fn();
    render(
      <label>
        Device
        <Select value="" onChange={onChange}>
          <option value="">All devices</option>
          <option value="1">Test device</option>
        </Select>
      </label>,
    );
    const select = screen.getByRole("combobox", { name: "Device" });
    expect(select.className).toBe(fieldClasses("md"));
    fireEvent.change(select, { target: { value: "1" } });
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it("has size sm and an error state", () => {
    render(
      <Select aria-label="Language" size="sm" invalid>
        <option value="en">English</option>
      </Select>,
    );
    const select = screen.getByRole("combobox", { name: "Language" });
    expect(select.className).toBe(fieldClasses("sm"));
    expect(select.getAttribute("aria-invalid")).toBe("true");
  });
});

describe("Textarea", () => {
  it("is a labelled text area with the border and text of an md field and its own rows", () => {
    render(<Textarea aria-label="Notes" rows={4} className="w-full" invalid />);
    const area = screen.getByRole("textbox", { name: "Notes" });
    expect(area.tagName).toBe("TEXTAREA");
    expect(area.getAttribute("rows")).toBe("4");
    expect(area.className).toBe(textareaClasses("w-full"));
    expect(area.getAttribute("aria-invalid")).toBe("true");
  });
});

describe("control heights", () => {
  it("are 36 px (md) and 28 px (sm) for buttons and fields alike", () => {
    expect(CONTROL_HEIGHT_PX).toEqual({ md: 36, sm: 28 });
    // Tailwind's spacing unit is 4 px: h-9 = 36 px, h-7 = 28 px.
    const units = { md: "9", sm: "7" } as const;
    for (const size of ["md", "sm"] as const) {
      expect(Number(units[size]) * 4).toBe(CONTROL_HEIGHT_PX[size]);
      expect(fieldClasses(size)).toContain(`h-${units[size]}`);
      expect(buttonClasses("primary", size)).toContain(`min-h-${units[size]}`);
    }
  });

  it("use the same border colour and the same disabled look for fields and secondary buttons", () => {
    expect(fieldClasses("md")).toContain("border-line-strong");
    expect(buttonClasses("secondary", "md")).toContain("border-line-strong");
    expect(fieldClasses("md")).toContain("disabled:opacity-50");
    expect(textareaClasses()).toContain("disabled:opacity-50");
  });
});
