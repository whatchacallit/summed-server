"""Convert Excel sheet to XSONL format."""
import srsly
import typer
import warnings
from pathlib import Path
import pandas
import json


def convert(
    lang: str = "en",
    input_path: Path = Path("../assets/docs_doctypes_all.xlsx"),
    sheet_name: str = "Sheet1",
    output_path: Path = Path("../assets/docs_doctypes_all.jsonl"),
    append: bool = False,
):
    # Read excel document
    df = pandas.read_excel(input_path, sheet_name=sheet_name)
    # Convert excel json
    as_json = df.to_json(orient="records")
    json_input = json.loads(as_json)
    # print(type(json_input))
    srsly.write_jsonl(
        path=output_path, lines=json_input, append=append, append_new_line=True
    )


if __name__ == "__main__":
    typer.run(convert)
