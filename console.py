"""
Інтерактивна та CLI-консоль для генератора постів Gemini AI.
Створює пости про треки з YouTube та зображення українською мовою,
надає можливість перегляду, редагування та збереження у файл posts.json.
"""

import sys
import argparse
from typing import Optional

# Забезпечення правильного кодування UTF-8 у консолі Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from core.models import PostStatus
from services.post_generator import PostGeneratorService


def print_banner():
    print("=" * 65)
    print(" 🎵 [GEMINI AI] КОНСОЛЬ ГЕНЕРАЦІЇ ТА РЕДАГУВАННЯ ПОСТІВ")
    print("=" * 65)


def display_post(post):
    print("\n" + "-" * 60)
    print(f"🆔 ID поста:    {post.id}")
    print(f"📌 Статус:      [{post.status.value.upper()}]")
    print(f"🏷️  Джерело:     {post.source_type.value} -> {post.source_ref}")
    print(f"📅 Створено:    {post.created_at}")
    print(f"📝 Заголовок:   {post.title}")
    print("-" * 60)
    print(post.content)
    print("-" * 60)
    if post.hashtags:
        print("🏷️  Хештеги:     " + " ".join(post.hashtags))
    if post.review_notes:
        print(f"💬 Нотатка:     {post.review_notes}")
    print("-" * 60)


def prompt_edit_post(service: PostGeneratorService, post_id: str):
    post = service.get_post(post_id)
    if not post:
        print(f"[!] Пост з ID '{post_id}' не знайдено.")
        return

    display_post(post)
    print("\n✏️  МЕНЮ РЕДАГУВАННЯ:")
    print("1. Змінити заголовок")
    print("2. Змінити текст поста")
    print("3. Змінити статус (draft, reviewed, approved, published)")
    print("4. Додати нотатку рецензента")
    print("5. Затвердити пост (APPROVED)")
    print("0. Назад")

    choice = input("\nОберіть дію (0-5): ").strip()
    if choice == "1":
        new_title = input(f"Введіть новий заголовок (поточний: {post.title}):\n> ").strip()
        if new_title:
            service.edit_post(post_id, new_title=new_title)
            print("[✓] Заголовок оновлено.")
    elif choice == "2":
        print("Введіть новий текст (вводьте рядки, для завершення натисніть Enter на порожньому рядку):")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        new_content = "\n".join(lines).strip()
        if new_content:
            service.edit_post(post_id, new_content=new_content)
            print("[✓] Текст поста оновлено.")
    elif choice == "3":
        print("Доступні статуси: draft (чернетка), reviewed (перевірено), approved (затверджено), published (опубліковано)")
        st = input("Введіть статус: ").strip().lower()
        try:
            status_enum = PostStatus(st)
            service.edit_post(post_id, new_status=status_enum)
            print(f"[✓] Статус оновлено на {status_enum.value}.")
        except ValueError:
            print("[!] Невідомий статус.")
    elif choice == "4":
        notes = input("Введіть нотатку рецензента:\n> ").strip()
        service.edit_post(post_id, review_notes=notes)
        print("[✓] Нотатку збережено.")
    elif choice == "5":
        service.approve_post(post_id)
        print("[✓] Пост успішно затверджено (APPROVED).")


def interactive_menu():
    service = PostGeneratorService()

    while True:
        print_banner()
        print("1. 🎵 Згенерувати пост про пісню (YouTube посилання або назва)")
        print("2. 🖼️ Згенерувати пост за зображенням (обкладинка, фото, постер)")
        print("3. 📋 Переглянути всі збережені пости з posts.json")
        print("4. 🔍 Рецензувати та відредагувати конкретний пост")
        print("5. ❌ Видалити пост")
        print("0. 🚪 Вийти")
        print("=" * 65)

        choice = input("Оберіть пункт (0-5): ").strip()

        if choice == "1":
            print("\n--- Генерація поста про пісню / YouTube ---")
            query = input("Введіть посилання на YouTube або назву пісні та виконавця:\n> ").strip()
            if not query:
                print("[!] Введення не може бути порожнім.")
                continue
            instructions = input("Додаткові побажання до стилю/тону (натисніть Enter, щоб пропустити):\n> ").strip()

            print("\n⏳ Отримання метаданих та генерація поста через Gemini AI українською мовою...")
            try:
                post = service.create_post_from_song(
                    query,
                    custom_instructions=instructions if instructions else None,
                )
                print("[✓] Пост створено та збережено в posts.json!")
                display_post(post)

                do_edit = input("\nБажаєте відредагувати або перевірити цей пост зараз? (y/n / т/н): ").strip().lower()
                if do_edit in ("y", "yes", "т", "так"):
                    prompt_edit_post(service, post.id)
            except Exception as e:
                print(f"[!] Помилка під час генерації поста: {e}")

        elif choice == "2":
            print("\n--- Генерація поста за зображенням ---")
            img_path = input("Введіть шлях до файлу зображення (наприклад, sample_album_cover.png):\n> ").strip()
            if not img_path:
                print("[!] Шлях не може бути порожнім.")
                continue
            instructions = input("Додатковий контекст чи побажання (натисніть Enter, щоб пропустити):\n> ").strip()

            print("\n⏳ Аналіз зображення та створення поста через Gemini AI українською мовою...")
            try:
                post = service.create_post_from_image(
                    img_path,
                    custom_instructions=instructions if instructions else None,
                )
                print("[✓] Пост створено та збережено в posts.json!")
                display_post(post)

                do_edit = input("\nБажаєте відредагувати або перевірити цей пост зараз? (y/n / т/н): ").strip().lower()
                if do_edit in ("y", "yes", "т", "так"):
                    prompt_edit_post(service, post.id)
            except Exception as e:
                print(f"[!] Помилка під час аналізу зображення: {e}")

        elif choice == "3":
            print("\n--- Збережені пости в posts.json ---")
            posts = service.get_all_posts()
            if not posts:
                print("У файлі posts.json ще немає збережених постів.")
            else:
                for idx, p in enumerate(posts, start=1):
                    print(f"{idx}. [{p.status.value.upper()}] ID: {p.id} | {p.title} ({p.source_type.value})")

        elif choice == "4":
            posts = service.get_all_posts()
            if not posts:
                print("[!] Немає постів для рецензування.")
                continue
            
            print("\nОстанні пости:")
            for p in posts[:5]:
                print(f" - {p.id}: {p.title} [{p.status.value}]")

            post_id = input("\nВведіть ID поста для перегляду/редагування:\n> ").strip()
            if post_id:
                prompt_edit_post(service, post_id)

        elif choice == "5":
            post_id = input("Введіть ID поста для видалення:\n> ").strip()
            if post_id:
                confirm = input(f"Ви впевнені, що хочете видалити пост {post_id}? (y/n / т/н): ").strip().lower()
                if confirm in ("y", "yes", "т", "так"):
                    if service.delete_post(post_id):
                        print("[✓] Пост видалено.")
                    else:
                        print("[!] Пост з таким ID не знайдено.")

        elif choice == "0":
            print("До побачення!")
            break
        else:
            print("[!] Невірний вибір. Оберіть пункт від 0 до 5.")

        input("\nНатисніть Enter для продовження...")


def cli_args_mode():
    parser = argparse.ArgumentParser(description="Gemini AI Генератор постів про треки та зображення")
    subparsers = parser.add_subparsers(dest="command", help="Доступні команди")

    # Song command
    song_parser = subparsers.add_parser("song", help="Створити пост за YouTube посиланням або назвою пісні")
    song_parser.add_argument("query", help="YouTube посилання або назва треку")
    song_parser.add_argument("--instructions", "-i", default=None, help="Власні інструкції щодо стилю")

    # Image command
    img_parser = subparsers.add_parser("image", help="Створити пост на основі аналізу зображення")
    img_parser.add_argument("path", help="Шлях до зображення")
    img_parser.add_argument("--instructions", "-i", default=None, help="Власні побажання щодо аналізу")

    # List command
    subparsers.add_parser("list", help="Показати список збережених постів")

    # Review command
    rev_parser = subparsers.add_parser("review", help="Переглянути та відредагувати пост")
    rev_parser.add_argument("id", help="ID поста")

    # Approve command
    app_parser = subparsers.add_parser("approve", help="Затвердити пост")
    app_parser.add_argument("id", help="ID поста")

    args = parser.parse_args()

    if not args.command:
        interactive_menu()
        return

    service = PostGeneratorService()

    if args.command == "song":
        print(f"Генерація поста для треку: {args.query}...")
        post = service.create_post_from_song(args.query, custom_instructions=args.instructions)
        display_post(post)
        print(f"[✓] Збережено в posts.json (ID: {post.id})")

    elif args.command == "image":
        print(f"Аналіз зображення: {args.path}...")
        post = service.create_post_from_image(args.path, custom_instructions=args.instructions)
        display_post(post)
        print(f"[✓] Збережено в posts.json (ID: {post.id})")

    elif args.command == "list":
        posts = service.get_all_posts()
        print(f"\n--- Збережені пости ({len(posts)}) ---")
        for p in posts:
            print(f"[{p.status.value.upper()}] {p.id} | {p.title} ({p.source_type.value})")

    elif args.command == "review":
        prompt_edit_post(service, args.id)

    elif args.command == "approve":
        post = service.approve_post(args.id)
        if post:
            print(f"[✓] Пост {args.id} позначено як APPROVED.")
        else:
            print(f"[!] Пост {args.id} не знайдено.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli_args_mode()
    else:
        interactive_menu()
