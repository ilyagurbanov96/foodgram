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
        existing_ingredients = set(Ingredient.objects.values_list(
            'name', flat=True)
        )

        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row.get('name')
                measurement_unit = row.get('measurement_unit')

                if name not in existing_ingredients:
                    ingredients_to_create.append(Ingredient(
                        name=name, measurement_unit=measurement_unit)
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Ингредиент "{name}" уже существует.'
                        )
                    )

        if ingredients_to_create:
            Ingredient.objects.bulk_create(
                ingredients_to_create, ignore_conflicts=True
            )
            for ingredient in ingredients_to_create:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Ингредиент "{ingredient.name}" успешно добавлен.'
                    )
                )
        else:
            self.stdout.write(self.style.NOTICE
                              ('Нет новых ингредиентов для добавления.')
                              )
