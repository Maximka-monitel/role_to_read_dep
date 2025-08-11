"""
Модуль обработки CSV файлов и генерации XML
Ответственность: бизнес-логика конвертации CSV в XML
"""

import logging
from typing import List, Dict, Set, Callable
from lxml import etree

# Импортируем необходимые модули с относительными путями
from .csv_reader import (
    read_encoding, iter_csv_rows, collect_csv_structure, 
    collect_all_children, check_required_fields, gen_uid
)
from .xml_generator import create_access_generator

# Вместо констант:
from .config_manager import get_config_value

class CSVProcessor:
    def __init__(self):
        self.required_fields = get_config_value('csv_processing.required_fields')
        self.model_version = get_config_value('csv_processing.model_version')
        # и т.д.


class CSVProcessor:
    """Класс для обработки CSV файлов и генерации XML."""
    
    def __init__(self):
        """Инициализация процессора."""
        self.required_fields = get_config_value('csv_processing.required_fields')
        self.model_version = get_config_value('csv_processing.model_version')
        self.model_name = get_config_value('csv_processing.model_name')
        self.role_template = get_config_value('csv_processing.role_template')
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
        
        Args:
            folder_uid: UID папки для ролей
            csv_file_path: путь к CSV файлу
            xml_file_path: путь к выходному XML файлу
            logger: логгер
            allow_headdep_recursive: разрешить рекурсивный доступ
            
        Returns:
            bool: True если обработка успешна
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
                
                datagroup_uid = gen_uid()
                datagroup_map[dep_uid] = datagroup_uid
                
                xml_generator.add_data_group(
                    xf, datagroup_uid, f'{org_name}\\{dep_name}',
                    "50000dc6-0000-0000-c000-0000006d746c"  # фиксированный родитель
                )
                
                # Добавляем ObjectReference
                objref_uid = gen_uid()
                with xf.element('{%s}ObjectReference' % NSMAP['cim'], 
                               attrib={'{%s}about' % NSMAP['rdf']: "#_" + objref_uid}):
                    xf.write(etree.Element('{%s}ObjectReference.objectUid' % NSMAP['cim'], 
                                         text=dep_uid))
                    xf.write(etree.Element('{%s}ObjectReference.Group' % NSMAP['cim'], 
                                         attrib={'{%s}resource' % NSMAP['rdf']: "#_" + datagroup_uid}))

            # Обрабатываем строки CSV и создаем роли
            for line_num, row in iter_csv_rows(csv_file_path, encoding, self.required_fields, logger):
                dep_uid = row['dep_uid']
                org_name = row.get('org_name', '')
                dep_name = row.get('dep_name', '')
                
                # Определяем к каким элементам данных даем доступ
                data_items_uids = []
                if dep_uid in headdep_uids and allow_headdep_recursive:
                    # Рекурсивный доступ ко всем потомкам
                    all_included = collect_all_children(dep_tree, dep_uid)
                    data_items_uids = [datagroup_map[x] for x in all_included if x in datagroup_map]
                    uids_str = ', '.join(sorted(all_included))
                    logger.info(f"Строка {line_num}: Добавляется роль: {self.role_template}, "
                              f"режим рекурсивного поиска ={allow_headdep_recursive}, "
                              f"headdep_uid={dep_uid}, доступ к {len(data_items_uids)} подразделениям: [{uids_str}]")
                else:
                    # Доступ только к конкретному подразделению
                    if dep_uid in datagroup_map:
                        data_items_uids = [datagroup_map[dep_uid]]
                        mode_info = f"headdep_uid={dep_uid} (только своё подразделение)" if dep_uid in headdep_uids else f"dep_uid={dep_uid}"
                        logger.info(f"Строка {line_num}: Добавляется роль: {self.role_template}, "
                                  f"режим рекурсивного поиска ={allow_headdep_recursive}, {mode_info}")

                # Создаем роль с привилегиями
                role_name = self.role_template.format(org_name=org_name, dep_name=dep_name)
                xml_generator.add_role_with_privilege(
                    xf, role_name, folder_uid, data_items_uids
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