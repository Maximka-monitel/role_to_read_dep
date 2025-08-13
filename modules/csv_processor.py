"""
Модуль обработки CSV файлов и генерации XML
Ответственность: бизнес-логика конвертации CSV в XML
"""

import logging
from typing import List, Dict, Set, Callable
import lxml.etree as etree

# Импортируем необходимые модули с относительными путями
from .csv_reader import (
    read_encoding, iter_csv_rows, collect_csv_structure,
    collect_all_children, check_required_fields, gen_uid
)
from .xml_generator import create_access_generator
from .config_manager import get_config_value


class CSVProcessor:
    """Класс для обработки CSV файлов и генерации XML."""

    def __init__(self):
        """Инициализация процессора."""
        self.required_fields = get_config_value(
            'csv_processing.required_fields')
        self.model_version = get_config_value('csv_processing.model_version')
        self.model_name = get_config_value('csv_processing.model_name')
        self.role_template = get_config_value('csv_processing.role_template')
        self.role_template_with_headdep = get_config_value('csv_processing.role_template_with_headdep') or \
            "Чтение записей по подр-ю {org_name}\\{headdep_name}\\{dep_name}"
        self.parent_field = get_config_value('csv_processing.parent_field')

    def process_csv_file_stream(
        self,
        folder_uid: str,
        csv_file_path: str,
        xml_file_path: str,
        logger: logging.Logger,
        allow_headdep_recursive: bool = True
    ) -> bool:
        """
        Потоковая обработка CSV-файла с генерацией XML.
        """
        logger.info(f"Старт обработки файла {csv_file_path} → {xml_file_path}")

        try:
            encoding = read_encoding(csv_file_path)
        except Exception as e:
            logger.error(f"Ошибка чтения CSV-файла {csv_file_path}: {e}")
            return False

        # Собираем информацию о структуре
        dep_info, dep_tree = collect_csv_structure(
            csv_file_path, encoding, self.required_fields, self.parent_field, logger
        )
        headdep_uids = set(dep_tree.keys())
        datagroup_map = {}
        roles_added = 0

        # Создаем генератор XML
        xml_generator = create_access_generator()
        NSMAP = xml_generator.namespaces

        def generate_content(xf):
            """Генератор контента для XML файла."""
            nonlocal roles_added

            # Добавляем FullModel
            fullmodel_uid = xml_generator.add_full_model(
                xf, self.model_version, self.model_name
            )

            # Добавляем DataGroup для каждого подразделения
            for dep_uid, info in dep_info.items():
                org_name = info.get('org_name', '')
                dep_name = info.get('dep_name', '')
                dep_headdep_uid = info.get('dep_headdep_uid', None)

                # Определяем headdep_name для DataGroup
                headdep_name = None
                if dep_headdep_uid:
                    # Если есть dep_headdep_uid, получаем его имя из dep_info
                    headdep_info = dep_info.get(dep_headdep_uid, {})
                    headdep_name = headdep_info.get('dep_name', '')

                datagroup_uid = gen_uid()
                dg_uid, objref_uid = xml_generator.add_data_group(
                    xf, org_name, dep_name, dep_uid, datagroup_uid, headdep_name
                )
                datagroup_map[dep_uid] = dg_uid

            # Обрабатываем строки CSV и создаем роли
            for line_num, row in iter_csv_rows(csv_file_path, encoding, self.required_fields, logger):
                dep_uid = row['dep_uid']
                org_name = row.get('org_name', '')
                dep_name = row.get('dep_name', '')
                dep_headdep_uid = row.get('dep_headdep_uid', None)

                # Определяем к каким элементам данных даем доступ
                data_items_uids = []

                # Определяем headdep_name
                headdep_name = None
                if dep_headdep_uid:
                    # Если есть dep_headdep_uid, получаем его имя из dep_info
                    headdep_info = dep_info.get(dep_headdep_uid, {})
                    headdep_name = headdep_info.get('dep_name', '')

                # Формируем список DataGroups для данной роли
                if dep_uid in headdep_uids and allow_headdep_recursive:
                    # Рекурсивный доступ ко всем потомкам
                    all_included = collect_all_children(dep_tree, dep_uid)
                    data_items_uids = [datagroup_map[x]
                                       for x in all_included if x in datagroup_map]
                else:
                    # Доступ только к текущему подразделению
                    if dep_uid in datagroup_map:
                        data_items_uids = [datagroup_map[dep_uid]]

                # Формируем название роли
                if headdep_name:
                    role_name = self.role_template_with_headdep.format(
                        org_name=org_name, headdep_name=headdep_name, dep_name=dep_name
                    )
                else:
                    role_name = self.role_template.format(
                        org_name=org_name, dep_name=dep_name
                    )

                # Логирование информации о роли
                if dep_headdep_uid:
                    logger.info(f"Строка {line_num}: Добавляется роль: {role_name}, "
                                f"headdep_uid={dep_headdep_uid}, dep_uid={dep_uid}")
                else:
                    logger.info(f"Строка {line_num}: Добавляется роль: {role_name}, "
                                f"dep_uid={dep_uid}")

                # Создаем роль с привилегиями
                xml_generator.add_role_with_privilege(
                    xf, org_name, dep_name, folder_uid, data_items_uids, headdep_name
                )
                roles_added += 1

        try:
            xml_generator.generate_xml(xml_file_path, generate_content)
            logger.info(f"Завершена обработка файла. Всего добавлено ролей: {roles_added}. "
                        f"XML сохранён: {xml_file_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка генерации XML-файла {xml_file_path}: {e}")
            return False


class BatchProcessor:
    """Класс для пакетной обработки CSV файлов."""

    def __init__(self):
        """Инициализация пакетного процессора."""
        self.csv_processor = CSVProcessor()

    def process_file_list(
        self,
        folder_uid: str,
        csv_dir: str,
        file_list: List[str],
        logger_factory: Callable[[str], logging.Logger],
        allow_headdep_recursive: bool = True
    ) -> Dict[str, bool]:
        """
        Обрабатывает список CSV файлов.

        Args:
            folder_uid: UID папки для ролей
            csv_dir: директория с CSV файлами
            file_list: список файлов для обработки
            logger_factory: фабрика логгеров
            allow_headdep_recursive: разрешить рекурсивный доступ

        Returns:
            Dict[str, bool]: результаты обработки файлов
        """
        from pathlib import Path

        results = {}

        for csv_filename in file_list:
            # Формируем пути
            csv_file_path = str(Path(csv_dir) / csv_filename)
            xml_filename = Path(csv_filename).stem + '.xml'
            xml_file_path = str(Path(csv_dir) / xml_filename)

            # Создаем логгер для этого файла
            logger = logger_factory(csv_filename)

            # Обрабатываем файл
            success = self.csv_processor.process_csv_file_stream(
                folder_uid, csv_file_path, xml_file_path, logger,
                allow_headdep_recursive=allow_headdep_recursive
            )

            results[csv_filename] = success

        return results


# Фабричные функции для удобства
def create_csv_processor() -> CSVProcessor:
    """Создает процессор CSV файлов."""
    return CSVProcessor()


def create_batch_processor() -> BatchProcessor:
    """Создает пакетный процессор."""
    return BatchProcessor()


# Обратная совместимость
def process_csv_file_stream(
    folder_uid: str,
    csv_dir: str,
    csv_filename: str,
    log_dir: str,
    logger: logging.Logger,
    allow_headdep_recursive: bool = True
):
    """Совместимость с предыдущей версией."""
    from pathlib import Path
    processor = CSVProcessor()
    csv_file_path = str(Path(csv_dir) / csv_filename)
    xml_filename = Path(csv_filename).stem + '.xml'
    xml_file_path = str(Path(csv_dir) / xml_filename)
    return processor.process_csv_file_stream(
        folder_uid, csv_file_path, xml_file_path, logger, allow_headdep_recursive
    )
