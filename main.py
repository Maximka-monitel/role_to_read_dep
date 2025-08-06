import chardet
import os
import uuid
import csv
from lxml import etree
from lxml.etree import xmlfile
from datetime import datetime
import logging
import sys
from typing import List, Dict, Set, Callable, Optional

NSMAP = {
    'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    'md': "http://iec.ch/TC57/61970-552/ModelDescription/1#",
    'cim': "http://monitel.com/2021/schema-access#"
}

REQUIRED_FIELDS = ['org_name', 'dep_name', 'dep_uid']
MODEL_VERSION = "2025-03-04(11.7.1.7)"
MODEL_NAME = "Access"
ROLE_TEMPLATE='Чтение записей под подр-ю {org_name}\\{dep_name}'

def gen_uid() -> str:
    """Генерирует уникальный идентификатор."""
    return str(uuid.uuid4())

def check_required_fields(row: dict, required_fields: List[str]) -> list[bool, str]:
    """Проверяет обязательные поля в записи CSV."""
    for field in required_fields:
        val = row.get(field)
        if val is None or not val.strip():
            return False, f"Поле '{field}' отсутствует или пустое"
    return True, ""

def make_log_dir(csv_dir: str) -> str:
    """Создаёт директорию для логов."""
    log_dir = os.path.join(csv_dir, "log")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def setup_logger(log_dir: str, csv_filename: str, callback: Optional[Callable[[str], None]] = None) -> logging.Logger:
    """Настраивает логгер для файла."""
    basename = os.path.splitext(os.path.basename(csv_filename))[0]
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(log_dir, f"{basename}_{date_str}.log")
    logger = logging.getLogger(log_path)
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s", "%Y-%m-%d %H:%M:%S")
    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.handlers = []
    logger.addHandler(file_handler)
    if callback:
        ui_handler = UILogHandler(callback)
        ui_handler.setFormatter(fmt)
        logger.addHandler(ui_handler)
    return logger

class UILogHandler(logging.Handler):
    """Handler для вывода логов в интерфейс."""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        try:
            msg = self.format(record)
            self.callback(msg + "\n")
        except Exception:
            pass

def read_encoding(file_path: str) -> str:
    """Определяет кодировку файла."""
    with open(file_path, 'rb') as f:
        rawdata = f.read(10000)
    encoding = chardet.detect(rawdata)['encoding']
    if encoding is None:
        raise ValueError(f"Не удалось определить кодировку файла {file_path}")
    return encoding

def iter_csv_rows(csv_file_path: str, encoding: str, required_fields: List[str], logger: logging.Logger):
    """Генератор: итерирует валидные строки CSV с номером строки."""
    with open(csv_file_path, encoding=encoding) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for line_num, row in enumerate(reader, start=2):
            ok, err_msg = check_required_fields(row, required_fields)
            if not ok:
                logger.error(f"Строка {line_num}: {err_msg}. Строка: {row}")
                continue
            yield line_num, row

def collect_dep_info_and_tree(csv_file_path: str, encoding: str, logger: logging.Logger):
    """Собирает dep_info и dep_tree одним проходом по CSV."""
    dep_info: Dict[str, tuple] = {}
    dep_tree: Dict[str, Set[str]] = {}
    with open(csv_file_path, encoding=encoding) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            ok, _ = check_required_fields(row, REQUIRED_FIELDS)
            if not ok:
                continue
            dep_uid = row['dep_uid']
            dep_headdep_uid = row.get('dep_headdep_uid', '').strip()
            org_name = row.get('org_name', '')
            dep_name = row.get('dep_name', '')
            dep_info[dep_uid] = (org_name, dep_name, dep_headdep_uid)
            if dep_headdep_uid:
                dep_tree.setdefault(dep_headdep_uid, set()).add(dep_uid)
    return dep_info, dep_tree

def collect_all_children(dep_tree: Dict[str, Set[str]], head_uid: str) -> Set[str]:
    """Рекурсивно собирает UID всех потомков и самого head_uid."""
    res = set()
    def crawler(uid: str):
        res.add(uid)
        for ch in dep_tree.get(uid, []):
            if ch not in res:
                crawler(ch)
    crawler(head_uid)
    return res

def process_csv_file_stream(
    folder_uid: str,
    csv_dir: str,
    csv_filename: str,
    log_dir: str,
    logger: logging.Logger
) -> None:
    """
    Потоковая обработка большого CSV-файла.
    Все элементы XML пишутся по мере чтения строк.
    """
    xml_filename = os.path.splitext(csv_filename)[0] + '.xml'
    csv_file_path = os.path.join(csv_dir, csv_filename)
    xml_file_path = os.path.join(csv_dir, xml_filename)
    logger.info(f"Старт обработки файла {csv_filename} → {xml_filename}")

    try:
        encoding = read_encoding(csv_file_path)
    except Exception as e:
        logger.error(f"Ошибка чтения CSV-файла {csv_filename}: {e}")
        return

    # Первый проход — строим dep_info и dep_tree
    dep_info, dep_tree = collect_dep_info_and_tree(csv_file_path, encoding, logger)
    headdep_uids = set(dep_tree.keys())
    datagroup_map: Dict[str, str] = {}

    roles_added = 0

    try:
        with xmlfile(xml_file_path, encoding='utf-8') as xf:
            with xf.element('{%s}RDF' % NSMAP['rdf'], nsmap=NSMAP):
                # Метаинформация
                fullmodel_uid = gen_uid()
                with xf.element('{%s}FullModel' % NSMAP['md'], attrib={'{%s}about' % NSMAP['rdf']: '#_' + fullmodel_uid}):
                    time_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
                    xf.write(etree.Element('{%s}Model.created' % NSMAP['md'], text=time_str + "Z"))
                    xf.write(etree.Element('{%s}Model.version' % NSMAP['md'], text=MODEL_VERSION))
                    xf.write(etree.Element('{http://monitel.com/2014/schema-cim16#}Model.name', text=MODEL_NAME))

                # --- Записываем DataGroups и ObjectReferences
                for dep_uid, (org_name, dep_name, _parent_uid) in dep_info.items():
                    datagroup_uid = gen_uid()
                    datagroup_map[dep_uid] = datagroup_uid
                    with xf.element('{%s}DataGroup' % NSMAP['cim'], attrib={'{%s}about' % NSMAP['rdf']: "#_" + datagroup_uid}):
                        xf.write(etree.Element('{%s}IdentifiedObject.name' % NSMAP['cim'], text=f'{org_name}\\{dep_name}'))
                        xf.write(etree.Element('{%s}IdentifiedObject.ParentObject' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"}))
                        xf.write(etree.Element('{%s}DataItem.isHostRestricted' % NSMAP['cim'], text='false'))
                        xf.write(etree.Element('{%s}DataItem.isUserRestricted' % NSMAP['cim'], text='true'))
                        xf.write(etree.Element('{%s}DataItem.Category' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_20000db8-0000-0000-c000-0000006d746c"}))
                        xf.write(etree.Element('{%s}DataGroup.Class' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"}))
                        objref_uid = gen_uid()
                        xf.write(etree.Element('{%s}DataGroup.Objects' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + objref_uid}))
                        # ObjectReference
                        with xf.element('{%s}ObjectReference' % NSMAP['cim'], attrib={'{%s}about' % NSMAP['rdf']: "#_" + objref_uid}):
                            xf.write(etree.Element('{%s}ObjectReference.objectUid' % NSMAP['cim'], text=dep_uid))
                            xf.write(etree.Element('{%s}ObjectReference.Group' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + datagroup_uid}))

                # --- Пишем Role/Privilege по строкам CSV
                for line_num, row in iter_csv_rows(csv_file_path, encoding, REQUIRED_FIELDS, logger):
                    dep_uid = row['dep_uid']
                    org_name = row.get('org_name', '')
                    dep_name = row.get('dep_name', '')
                    role_uid = gen_uid()
                    privilege_uid = gen_uid()
                    with xf.element('{%s}Role' % NSMAP['cim'], attrib={'{%s}about' % NSMAP['rdf']: "#_" + role_uid}):
                        xf.write(etree.Element('{%s}IdentifiedObject.name' % NSMAP['cim'], text=ROLE_TEMPLATE))
                        xf.write(etree.Element('{%s}IdentifiedObject.ParentObject' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + folder_uid}))
                        xf.write(etree.Element('{%s}Role.isHost' % NSMAP['cim'], text='false'))
                        xf.write(etree.Element('{%s}Role.isUser' % NSMAP['cim'], text='true'))
                        xf.write(etree.Element('{%s}Role.kind' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "cim:RoleKind.allow"}))
                        xf.write(etree.Element('{%s}Role.Privileges' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + privilege_uid}))
                    with xf.element('{%s}Privilege' % NSMAP['cim'], attrib={'{%s}about' % NSMAP['rdf']: "#_" + privilege_uid}):
                        xf.write(etree.Element('{%s}Privilege.Role' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + role_uid}))
                        if dep_uid in headdep_uids:
                            all_included = collect_all_children(dep_tree, dep_uid)
                            datagroup_uids = [datagroup_map[x] for x in all_included if x in datagroup_map]
                            uids_str = ', '.join(sorted(all_included))
                            for dg_uid in datagroup_uids:
                                xf.write(etree.Element('{%s}Privilege.DataItems' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + dg_uid}))
                            logger.info(
                                f"Строка {line_num}: Добавляется роль: {ROLE_TEMPLATE}, headdep_uid={dep_uid}, доступ к {len(datagroup_uids)} подразделениям: [{uids_str}]")
                        else:
                            xf.write(etree.Element('{%s}Privilege.DataItems' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + datagroup_map[dep_uid]}))
                            logger.info(
                                f"Строка {line_num}: Добавляется роль: {ROLE_TEMPLATE}, dep_uid={dep_uid}")
                        xf.write(etree.Element('{%s}Privilege.Operation' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_2000065d-0000-0000-c000-0000006d746c"}))
                    roles_added += 1
        logger.info(f"Завершена обработка файла. Всего добавлено ролей: {roles_added}. XML сохранён: {xml_filename}")
    except Exception as e:
        logger.error(f"Ошибка генерации XML-файла {xml_filename}: {e}")

def process_all_csv_from_list(
    folder_uid: str,
    csv_dir: str,
    file_list: List[str],
    log_callback: Optional[Callable[[str], None]] = None
):
    """Обрабатывает все указанные CSV-файлы."""
    log_dir = make_log_dir(csv_dir)
    for csv_filename in file_list:
        logger = setup_logger(log_dir, csv_filename, log_callback)
        process_csv_file_stream(folder_uid, csv_dir, csv_filename, log_dir, logger)

def debug_cli():
    """CLI для пакетного запуска."""
    print("="*50)
    print("Пакетный конвертер CSV ➔ XML (поточн. генерация XML)")
    if len(sys.argv) >= 3:
        folder_uid = sys.argv[1]
        csv_dir = sys.argv[2]
    else:
        folder_uid = input('Введите UID папки для ролей: ').strip()
        csv_dir = input('Укажите папку с CSV (или . для текущей): ').strip() or '.'
    if not os.path.isdir(csv_dir):
        print(f"Папка не найдена: {csv_dir}")
        return
    all_files = [f for f in os.listdir(csv_dir) if f.lower().endswith('.csv') and f.lower() != 'sample.csv']
    if not all_files:
        print("Нет подходящих .csv файлов")
        return

    print("Будут обработаны файлы:")
    for f in all_files:
        print("  ", f)
    print("-"*25)
    def cli_log(msg):
        print(msg, end='' if msg.endswith('\n') else '\n')
    process_all_csv_from_list(folder_uid, csv_dir, all_files, log_callback=cli_log)
    print("Готово.")

if __name__ == '__main__':
    debug_cli()
