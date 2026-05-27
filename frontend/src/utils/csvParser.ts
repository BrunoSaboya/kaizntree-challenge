export interface RawProductRow {
  name: string;
  sku: string;
  unit_type: string;
  description: string;
  min_stock_quantity: string;
}

const KNOWN_FIELDS: (keyof RawProductRow)[] = [
  "name",
  "sku",
  "unit_type",
  "description",
  "min_stock_quantity",
];

export function parseCsvText(text: string): string[][] {
  const rows: string[][] = [];
  const normalized = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  let pos = 0;

  while (pos < normalized.length) {
    const row: string[] = [];
    while (pos < normalized.length && normalized[pos] !== "\n") {
      if (normalized[pos] === '"') {
        // quoted field
        pos++; // skip opening quote
        let field = "";
        while (pos < normalized.length) {
          if (normalized[pos] === '"') {
            if (normalized[pos + 1] === '"') {
              field += '"';
              pos += 2;
            } else {
              pos++; // skip closing quote
              break;
            }
          } else {
            field += normalized[pos++];
          }
        }
        row.push(field);
        if (normalized[pos] === ",") pos++;
      } else {
        let field = "";
        while (pos < normalized.length && normalized[pos] !== "," && normalized[pos] !== "\n") {
          field += normalized[pos++];
        }
        row.push(field);
        if (normalized[pos] === ",") pos++;
      }
    }
    if (normalized[pos] === "\n") pos++;
    if (row.length > 0 && !(row.length === 1 && row[0] === "")) {
      rows.push(row);
    }
  }

  return rows;
}

export function mapCsvToProducts(rows: string[][]): {
  mapped: RawProductRow[];
  unknownHeaders: string[];
} {
  if (rows.length < 2) return { mapped: [], unknownHeaders: [] };

  const headers = rows[0].map((h) => h.trim().toLowerCase());
  const unknownHeaders = headers.filter((h) => !KNOWN_FIELDS.includes(h as keyof RawProductRow));

  const mapped: RawProductRow[] = [];
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    const isBlank = row.every((cell) => cell.trim() === "");
    if (isBlank) continue;

    const obj: RawProductRow = {
      name: "",
      sku: "",
      unit_type: "",
      description: "",
      min_stock_quantity: "",
    };

    headers.forEach((header, idx) => {
      if (KNOWN_FIELDS.includes(header as keyof RawProductRow)) {
        obj[header as keyof RawProductRow] = (row[idx] ?? "").trim();
      }
    });

    mapped.push(obj);
  }

  return { mapped, unknownHeaders };
}
