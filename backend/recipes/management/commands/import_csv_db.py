import csv
from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Импорт ингредиентов из CSV файла'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Путь к CSV файлу')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row['name']
                measurement_unit = row['measurement_unit']
                ingredient, created = Ingredient.objects.get_or_create(
                    name=name,
                    measurement_unit=measurement_unit
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'''
                                                         Ингредиент "{name}"
                                                         успешно добавлен.'''))
                else:
                    self.stdout.write(self.style.WARNING(f'''
                                                         Ингредиент "{name}"
                                                         уже существует.'''))
