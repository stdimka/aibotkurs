def get_all_keywords(redis) -> list[str]:
    """
    Возвращает полный список ключевых слов
    """
    keywords = redis.smembers("keywords")
    return sorted(
        k.decode() if isinstance(k, bytes) else k
        for k in keywords
    )

def matches_keywords(redis, news: dict) -> bool:
    """
    Проверяет, содержит ли новость хотя бы одно ключевое слово.
    Ищем в title и summary.
    """
    keywords = get_all_keywords(redis)

    if not keywords:
        return True  # если фильтр пуст — пропускаем всё

    text = f"{news['title']} {news.get('summary', '')}".lower()

    return any(word.lower() in text for word in keywords)
