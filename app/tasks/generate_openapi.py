import json

from app.main import app


def main():
    with open("docs.json", "w") as f:
        json.dump(app.openapi(), f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
