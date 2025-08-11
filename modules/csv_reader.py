"""
Модуль чтения CSV файлов с поддержкой кодировок и валидации
Масштабируемый для любого проекта
"""

import chardet
import csv
import os
from typing import Dict, List, Tuple, Generator, Callable, Any
# Вместо констант:
from .config_manager import get_config_value

REQUIRED_FIELDS = get_config_value('csv_processing.required_fields')
PARENT_FIELD = get_config_value('csv_processing.parent_field')
DEFAULT_DELIMITER = get_config_value('csv_processing.parent_field')
DEFAULT_EXCLUDE_FILES = get_config_value('file_management.exclude_files')

# Добавьте в начало файла modules/csv_reader.py:
import uuid

def gen_uid() -> str:
    """Генерирует уникальный идентификатор."""
    return str(uuid.uuid4())

def read_encoding(file_path: str) -> str:
    """Определяет кодировку файла."""
    with open(file_path, 'rb') as f:
        rawdata = f.read(10000)
    encoding = chardet.detect(rawdata)['encoding']
    if encoding is None:
        raise ValueError(f"Не удалось определить кодировку файла {file_path}")
    return encoding


def check_required_fields(row: dict, required_fields: list) -> Tuple[bool, str]:
    """Проверяет обязательные поля в записи CSV."""
    for field in required_fields:
        val = row.get(field)
        if val is None or not val.strip():
            return False, f"Поле '{field}' отсутствует или пустое"
    return True, ""


def iter_csv_rows(
    csv_file_path: str, 
    encoding: str, 
    required_fields: list, 
    logger: Any = None,
    delimiter: str = ';'
) -> Generator[Tuple[int, Dict], None, None]:
    """
    Генератор: итерирует валидные строки CSV с номером строки.
    
    Args:
        csv_file_path: путь к CSV файлу
        encoding: кодировка файла
        required_fields: список обязательных полей
        logger: объект логгера (опционально)
        delimiter: разделитель в CSV (по умолчанию ';')
        
    Yields:
        Tuple[int, Dict]: номер строки и словарь с данными строки
    """
    with open(csv_file_path, encoding=encoding) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=delimiter)
        for line_num, row in enumerate(reader, start=2):
            ok, err_msg = check_required_fields(row, required_fields)
            if not ok:
                if logger:
                    logger.error(f"Строка {line_num}: {err_msg}. Строка: {row}")
                continue
            yield line_num, row


def collect_csv_structure(
    csv_file_path: str, 
    encoding: str, 
    required_fields: list,
    parent_field: str = None,
    logger: Any = None,
    delimiter: str = ';'
) -> Tuple[Dict, Dict]:
    """
    Собирает информацию о структуре данных из CSV.
    
    Args:
        csv_file_path: путь к CSV файлу
        encoding: кодировка файла
        required_fields: список обязательных полей
        parent_field: поле с ссылкой на родителя (для иерархии)
        logger: объект логгера (опционально)
        delimiter: разделитель в CSV
        
    Returns:
        Tuple[Dict, Dict]: (info_dict, tree_dict) - информация о записях и дерево иерархии
    """
    info_dict = {}
    tree_dict = {}
    
    with open(csv_file_path, encoding=encoding) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=delimiter)
        for row in reader:
            ok, _ = check_required_fields(row, required_fields)
            if not ok:
                continue
                
            # Извлекаем основную информацию
            record_id = row[required_fields[2]] if len(required_fields) > 2 else None
            if record_id:
                info_dict[record_id] = {
                    field: row.get(field, '') for field in row.keys()
                }
                
                # Строим дерево иерархии если указано поле родителя
                if parent_field and parent_field in row:
                    parent_id = row[parent_field].strip()
                    if parent_id:
                        tree_dict.setdefault(parent_id, set()).add(record_id)
    
    return info_dict, tree_dict


def collect_all_children(tree_dict: dict, parent_id: str) -> set:
    """
    Рекурсивно собирает ID всех потомков и самого родителя.
    
    Args:
        tree_dict: словарь иерархии {родитель: {потомки}}
        parent_id: ID родительского элемента
        
    Returns:
        set: множество всех потомков включая родителя
    """
    result = set()
    
    def crawler(uid: str):
        result.add(uid)
        for child in tree_dict.get(uid, []):
            if child not in result:
                crawler(child)
    
    crawler(parent_id)
    return result


def get_csv_files(directory: str, exclude_files: List[str] = None) -> List[str]:
    """
    Получает список CSV файлов в директории.
    
    Args:
        directory: путь к директории
        exclude_files: список файлов для исключения
        
    Returns:
        List[str]: список имен CSV файлов
    """
    if exclude_files is None:
        exclude_files = ['sample.csv']
    
    exclude_files = [f.lower() for f in exclude_files]
    all_files = [f for f in os.listdir(directory) 
                 if f.lower().endswith('.csv') 
                 and f.lower() not in exclude_files]
    return all_files


# Алиасы для обратной совместимости
detect_encoding = read_encoding
iterate_csv_rows = iter_csv_rows