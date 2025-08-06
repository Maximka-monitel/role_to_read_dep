import chardet
import os
import uuid
import csv
from lxml import etree
from datetime import datetime
import logging
import sys

def gen_uid():
    return str(uuid.uuid4())

def check_required_fields(row, required_fields):
    for field in required_fields:
        val = row.get(field)
        if val is None or not val.strip():
            return False, f"Поле '{field}' отсутствует или пустое"
    return True, ""

def create_rdf_root(NSMAP):
    rdf = etree.Element('{%s}RDF' % NSMAP['rdf'], nsmap=NSMAP)
    fullmodel = etree.SubElement(rdf, '{%s}FullModel' % NSMAP['md'], attrib={
        '{%s}about' % NSMAP['rdf']: '#_' + gen_uid()
    })
    time_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    etree.SubElement(fullmodel, '{%s}Model.created' % NSMAP['md']).text = time_str + "Z"
    etree.SubElement(fullmodel, '{%s}Model.version' % NSMAP['md']).text = "2025-03-04(11.7.1.7)"
    etree.SubElement(fullmodel, '{http://monitel.com/2014/schema-cim16#}Model.name').text = "Access"
    return rdf

def add_datagroup_structure(rdf, NSMAP, org_name, dep_name, dep_uid):
    datagroup_uid = gen_uid()
    objectref_uid = gen_uid()
    datagr = etree.SubElement(rdf, '{%s}DataGroup' % NSMAP['cim'], attrib={'{%s}about' % NSMAP['rdf']: "#_" + datagroup_uid})
    etree.SubElement(datagr, '{%s}IdentifiedObject.name' % NSMAP['cim']).text = f'{org_name}\\{dep_name}'
    etree.SubElement(datagr, '{%s}IdentifiedObject.ParentObject' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"})
    etree.SubElement(datagr, '{%s}DataItem.isHostRestricted' % NSMAP['cim']).text = 'false'
    etree.SubElement(datagr, '{%s}DataItem.isUserRestricted' % NSMAP['cim']).text = 'true'
    etree.SubElement(datagr, '{%s}DataItem.Category' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_20000db8-0000-0000-c000-0000006d746c"})
    etree.SubElement(datagr, '{%s}DataGroup.Class' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"})
    etree.SubElement(datagr, '{%s}DataGroup.Objects' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + objectref_uid})
    oref = etree.SubElement(rdf, '{%s}ObjectReference' % NSMAP['cim'], attrib={'{%s}about' % NSMAP['rdf']: "#_" + objectref_uid})
    etree.SubElement(oref, '{%s}ObjectReference.objectUid' % NSMAP['cim']).text = dep_uid
    etree.SubElement(oref, '{%s}ObjectReference.Group' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + datagroup_uid})
    return datagroup_uid

def add_role_structure_multiple_datagroups(rdf, NSMAP, org_name, dep_name, folder_uid, datagroup_uids):
    role_uid = gen_uid()
    privilege_uid = gen_uid()
    role = etree.SubElement(rdf, '{%s}Role' % NSMAP['cim'], attrib={
        '{%s}about' % NSMAP['rdf']: "#_" + role_uid
    })
    etree.SubElement(role, '{%s}IdentifiedObject.name' % NSMAP['cim']).text = f'Чтение записей под подр-ю {org_name}\\{dep_name}'
    etree.SubElement(role, '{%s}IdentifiedObject.ParentObject' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + folder_uid})
    etree.SubElement(role, '{%s}Role.isHost' % NSMAP['cim']).text = 'false'
    etree.SubElement(role, '{%s}Role.isUser' % NSMAP['cim']).text = 'true'
    etree.SubElement(role, '{%s}Role.kind' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "cim:RoleKind.allow"})
    etree.SubElement(role, '{%s}Role.Privileges' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + privilege_uid})
    priv = etree.SubElement(rdf, '{%s}Privilege' % NSMAP['cim'], attrib={'{%s}about' % NSMAP['rdf']: "#_" + privilege_uid})
    etree.SubElement(priv, '{%s}Privilege.Role' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + role_uid})
    for dg_uid in datagroup_uids:
        etree.SubElement(priv, '{%s}Privilege.DataItems' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + dg_uid})
    etree.SubElement(priv, '{%s}Privilege.Operation' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_2000065d-0000-0000-c000-0000006d746c"})

class UILogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        try:
            msg = self.format(record)
            self.callback(msg + "\n")
        except Exception:
            pass

def make_log_dir(csv_dir):
    log_dir = os.path.join(csv_dir, "log")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def setup_logger(log_dir, csv_filename, callback=None):
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

def process_all_csv_from_list(folder_uid, csv_dir, file_list, log_callback=None):
    NSMAP = {
        'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        'md': "http://iec.ch/TC57/61970-552/ModelDescription/1#",
        'cim': "http://monitel.com/2021/schema-access#"
    }
    required_fields = ['org_name', 'dep_name', 'dep_uid']

    log_dir = make_log_dir(csv_dir)

    for csv_filename in file_list:
        xml_filename = os.path.splitext(csv_filename)[0] + '.xml'
        logger = setup_logger(log_dir, csv_filename, log_callback)
        roles_added = 0
        try:
            csv_file_path = os.path.join(csv_dir, csv_filename)
            logger.info(f"Старт обработки файла {csv_filename} → {xml_filename}")

            try:
                with open(csv_file_path, 'rb') as f:
                    rawdata = f.read(10000)
                    detected = chardet.detect(rawdata)
                    enc = detected['encoding']
            except Exception as e:
                logger.error(f"Ошибка чтения CSV-файла {csv_filename}: {e}")
                continue

            dep_rows = []
            dep_info = {}
            try:
                with open(csv_file_path, encoding=enc) as csvfile:
                    reader = csv.DictReader(csvfile, delimiter=';')
                    for line_num, row in enumerate(reader, start=2):
                        ok, err_msg = check_required_fields(row, required_fields)
                        if not ok:
                            logger.error(f"Строка {line_num}: {err_msg}. Строка: {row}")
                            continue
                        dep_uid = row['dep_uid']
                        dep_name = row['dep_name']
                        dep_headdep_uid = row.get('dep_headdep_uid', '').strip()
                        org_name = row.get('org_name', '')
                        dep_rows.append((line_num, row))
                        dep_info[dep_uid] = (org_name, dep_name, dep_headdep_uid)
            except Exception as e:
                logger.error(f"Ошибка чтения CSV-файла {csv_filename}: {e}")
                continue

            # Определим все headdep_uids (те, кто встречается в dep_headdep_uid хотя бы раз)
            headdep_uids = set(
                filter(None, [row[1].get('dep_headdep_uid', '').strip() for row in dep_rows])
            )
            # Строим дерево: headdep_uid -> set(children dep_uid)
            dep_tree = {}
            for _ln, row in dep_rows:
                dep_uid = row['dep_uid']
                parent_uid = row.get('dep_headdep_uid', '').strip()
                if parent_uid:
                    dep_tree.setdefault(parent_uid, set()).add(dep_uid)
            # Вспомогательная функция сбора всех потомков (рекурсивно)
            def collect_all_children(head_uid):
                res = set()
                def crawler(uid):
                    res.add(uid)
                    for ch in dep_tree.get(uid, []):
                        if ch not in res:
                            crawler(ch)
                crawler(head_uid)
                return res

            rdf = create_rdf_root(NSMAP)
            datagroup_map = {}
            for dep_uid, (org_name, dep_name, _parent_uid) in dep_info.items():
                datagroup_uid = add_datagroup_structure(rdf, NSMAP, org_name, dep_name, dep_uid)
                datagroup_map[dep_uid] = datagroup_uid

            for line_num, row in dep_rows:
                dep_uid = row['dep_uid']
                org_name = row.get('org_name', '')
                dep_name = row.get('dep_name', '')
                try:
                    if dep_uid in headdep_uids:
                        all_included = collect_all_children(dep_uid)
                        datagroup_uids = [datagroup_map[x] for x in all_included if x in datagroup_map]
                        uids_str = ', '.join(sorted(all_included))
                        add_role_structure_multiple_datagroups(
                            rdf, NSMAP, org_name, dep_name, folder_uid, datagroup_uids)
                        logger.info(
                            f"Строка {line_num}: Добавляется роль: {org_name}\\{dep_name}, headdep_uid={dep_uid}, доступ к {len(datagroup_uids)} подразделениям: [{uids_str}]")
                    else:
                        add_role_structure_multiple_datagroups(
                            rdf, NSMAP, org_name, dep_name, folder_uid, [datagroup_map[dep_uid]])
                        logger.info(
                            f"Строка {line_num}: Добавляется роль: {org_name}\\{dep_name}, dep_uid={dep_uid}")
                    roles_added += 1
                except Exception as e:
                    logger.error(
                        f"Ошибка при обработке строки {line_num} в {csv_filename}: {type(e).__name__}: {e}")


            etree.indent(rdf, space="  ")
            xml_bytes = etree.tostring(rdf, xml_declaration=True, encoding='utf-8', pretty_print=True)
            out_path = os.path.join(csv_dir, xml_filename)
            try:
                with open(out_path, "wb") as f:
                    f.write(xml_bytes)
                logger.info(f"Завершена обработка файла. Всего добавлено ролей: {roles_added}. XML сохранён: {xml_filename}")
            except Exception as e:
                logger.error(f"Ошибка записи XML-файла {xml_filename}: {e}")
        except Exception as e:
            logger.error(f"Критическая ошибка при обработке файла {csv_filename}: {type(e).__name__}: {e}")



def debug_cli():
    print("="*50)
    print("Отладочный режим пакетного конвертера CSV ➔ XML.")
    if len(sys.argv) >= 3:
        folder_uid = sys.argv[1]
        csv_dir = sys.argv[2]
    else:
        folder_uid = input('Введите UID папки для ролей: ').strip()
        csv_dir = input('Укажите папку с CSV-файлами (или . для текущей): ').strip() or '.'
    if not os.path.isdir(csv_dir):
        print(f"Папка не найдена: {csv_dir}")
        return
    all_files = [f for f in os.listdir(csv_dir) if f.lower().endswith('.csv') and f.lower() != 'sample.csv']
    if not all_files:
        print("Нет подходящих .csv файлов в указанной папке.")
        return

    print("Будут обработаны файлы:")
    for f in all_files:
        print("  ", f)
    print("-"*30)

    def cli_log(msg):
        print(msg, end='' if msg.endswith('\n') else '\n')

    process_all_csv_from_list(folder_uid, csv_dir, all_files, log_callback=cli_log)
    print("Готово.")

if __name__ == '__main__':
    debug_cli()
