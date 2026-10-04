from app.tasks.fill_init_data import process_csv_post_to_schema


def test_csv_post_parser_removes_csv_list_quotes() -> None:
    post = process_csv_post_to_schema(
        {
            "text": "Привет 🎁",
            "rubrics": "['VK-1', 'VK-2']",
        }
    )

    assert post.text == "Привет 🎁"
    assert post.rubrics == ["VK-1", "VK-2"]
