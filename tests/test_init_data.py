from datetime import datetime

from app.tasks.fill_init_data import process_csv_post_to_schema


def test_csv_post_parser_removes_csv_list_quotes() -> None:
    post = process_csv_post_to_schema(
        {
            "text": "Привет 🎁",
            "created_date": "2019-07-25 12:42:13",
            "rubrics": "['VK-1', 'VK-2']",
        }
    )

    assert post.text == "Привет 🎁"
    assert post.rubrics == ["VK-1", "VK-2"]
    assert post.created_date == datetime(2019, 7, 25, 12, 42, 13)
