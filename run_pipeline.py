from celery import group, chain

from celery_app import celery_app
from app.tasks.parse_sites import parse_site_task
from app.tasks.filter import filter_posts_task
from app.redis_sync import get_sync_redis

from app.tasks.generate import generate_post_task


def get_all_source_names():
    redis = get_sync_redis()
    keys = redis.keys("site_sources:*")
    return [
        key.split(":")[1]
        for key in keys
    ]


def main():
    # --- Парсинг -----------------------------------------------------
    source_names = get_all_source_names()

    if not source_names:
        print("Нет источников")
        return

    parse_group = group(
        parse_site_task.s(source_name=name)
        for name in source_names
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
