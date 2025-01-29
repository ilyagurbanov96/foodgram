import csv

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Импорт ингредиентов из CSV файла'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv_file',
            type=str,
            default='data/ingredients.csv',
            help='Путь к CSV файлу'
        )

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        ingredients_to_create = []
        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row.get('name')
                measurement_unit = row.get('measurement_unit')
                ingredients_to_create.append(Ingredient(
                    name=name, measurement_unit=measurement_unit)
                )
        Ingredient.objects.bulk_create(
            ingredients_to_create, ignore_conflicts=True
        )
        existing_ingredients = set(Ingredient.objects.filter(
            name__in=[i.name for i in ingredients_to_create]
        ).values_list('name', flat=True))
        for ingredient in existing_ingredients:
            self.stdout.write(
                self.style.WARNING(f'''Ингредиент "{ingredient}"
                                   уже существует.''')
            )
        for ingredient in ingredients_to_create:
            if ingredient.name not in existing_ingredients:
                self.stdout.write(
                    self.style.SUCCESS(f'''Ингредиент "{ingredient.name}"
                                       успешно добавлен.''')
                )
