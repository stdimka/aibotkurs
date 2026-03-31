from celery import group, chain

from celery_app import celery_app
from app.tasks.parse_sites import parse_site_task
from app.tasks.filter import filter_posts_task
from app.redis_sync import get_sync_redis

from app.tasks.generate import generate_post_task
from app.tasks.parse_tg import parse_tg_task
from app.tasks.publish import publish_to_telegram_task

def get_all_source_names():
    redis = get_sync_redis()
    keys = redis.keys("site_sources:*")
    return [
        key.split(":")[1]
        for key in keys
    ]

def get_all_tg_names():
    redis = get_sync_redis()
    keys = redis.keys("tg_sources:*")
    return [
        key.split(":")[1]
        for key in keys
    ]


def main():
    source_site_names = get_all_source_names()
    source_tg_names = get_all_tg_names()

    if not (source_site_names or source_tg_names):
        print("Нет источников")
        return

    parse_group = group(
        [parse_site_task.s(source_name=name) for name in source_site_names] +
        [parse_tg_task.s(source_name=name) for name in source_tg_names]
    )

    result = parse_group.apply_async()

    print("Задачи запущены. Ждём результата...")

    total = result.get(timeout=300)  # ждём завершения всех
    print(f"Результаты: {total}")
    print(f'Всего сохранено "сырых" постов: {sum(total)}')

    # --- Фильтрация --------------------------------------------------

    filter_result = filter_posts_task.apply_async()
    print("Фильтрация запущена. Ждём результата...")

    filtered_count = filter_result.get(timeout=180)
    print(f"Отфильтровано: {filtered_count}")




    redis = get_sync_redis()
    filtered_keys = redis.keys("news:filtered:*")

    if not filtered_keys:
        print("Нет отфильтрованных новостей для генерации")
    else:
        print(f"Найдено отфильтрованных новостей: {len(filtered_keys)}")
        generate_group = group(
            generate_post_task.s(
                key.decode("utf-8") if isinstance(key, bytes) else key
            )
            for key in filtered_keys
        )

        try:
            gen_counts = generate_group.apply_async().get(timeout=600)
            total_generated = sum(x or 0 for x in gen_counts)
            print(f"Генерация завершена. Успешно сгенерировано: {total_generated}")
        except Exception as e:
            print(f"Ошибка при генерации: {type(e).__name__}: {e}")

    # --- Запуск публикации в Telegram --------------------------------

    print("Запуск публикации в Telegram...")

    redis = get_sync_redis()
    generated_keys = redis.keys("news:generated:*")

    if not generated_keys:
        print("Нет сгенерированных постов для публикации")
    else:
        unpublished_keys = []
        for raw_key in generated_keys:
            key_str = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else raw_key

            data = redis.hgetall(raw_key)  # data содержит bytes

            published_flag = data.get(b"is_published") or data.get("is_published")
            if published_flag is None:
                is_published = False
            else:
                flag_str = str(published_flag).strip().lower()
                is_published = flag_str in ("1", "true", "yes")

            if not is_published:
                unpublished_keys.append(key_str)

        if not unpublished_keys:
            print("Все сгенерированные посты уже опубликованы ранее.")
        else:
            print(f"Найдено неопубликованных постов: {len(unpublished_keys)}")

            publish_group = group(
                publish_to_telegram_task.s(key)
                for key in unpublished_keys
            )

            try:
                publish_results = publish_group.apply_async().get(timeout=300)
                total_published = sum(x or 0 for x in publish_results)
                print(f"Публикация завершена. Успешно опубликовано: {total_published} постов")
            except Exception as e:
                print(f"Ошибка при публикации: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()

# from celery import group, chord
#
# from celery_app import celery_app
# from app.tasks.parse_sites import parse_site_task
# from app.tasks.filter import filter_posts_task
# from app.redis_sync import get_sync_redis
# from app.tasks.generate import generate_post_task
#
#
# def get_all_source_names():
#     redis = get_sync_redis()
#     keys = redis.keys("site_sources:*")
#     return [
#         key.split(":")[1]
#         for key in keys
#     ]
#
#
# @celery_app.task
# def start_generation(_):
#     """
#     Callback после фильтрации.
#     Запускает генерацию постов по всем отфильтрованным новостям.
#
#     start_generation.s() требует наличие хотя бы одного аргумента.
#     Поэтому передаём символ подчёркивания "_"
#
#     return result.id - возвращаем id группы, где каждая из задач
#     запускается асинхронно
#
#     """
#
#     # --- Запуск генерации постов -------------------------------------
#
#     redis = get_sync_redis()
#     filtered_keys = redis.keys("news:filtered:*")
#
#     if not filtered_keys:
#         print("Нет отфильтрованных новостей для генерации")
#         return 0
#
#     print(f"Найдено отфильтрованных новостей: {len(filtered_keys)}")
#
#     generate_group = group(
#         generate_post_task.s(
#             key.decode("utf-8") if isinstance(key, bytes) else key
#         )
#         for key in filtered_keys
#     )
#
#     result = generate_group.apply_async()
#
#     print("Генерация постов запущена")
#
#     return result.id
#
#
# def main():
#     # --- Парсинг -----------------------------------------------------
#
#     source_names = get_all_source_names()
#
#     if not source_names:
#         print("Нет источников")
#         return
#
#     parse_group = group(
#         parse_site_task.s(source_name=name)
#         for name in source_names
#     )
#
#     print("Задачи запущены (parse -> filter -> generate)...")
#
#     # --- После завершения парсинга запускается фильтрация,
#     # --- затем генерация постов --------------------------------------
#
#     workflow = chord(parse_group)(
#         filter_posts_task.si() | start_generation.s()
#     )
#
#     print(f"Workflow запущен: {workflow.id}")
#
#
# if __name__ == "__main__":
#     main()
