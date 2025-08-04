import os
import uuid
import csv
from lxml import etree
import logging
from datetime import datetime

def gen_uid():
    """Генерирует уникальный идентификатор UUID4 в виде строки."""
    return str(uuid.uuid4())

# Префиксы пространств имён для RDF/XML
NSMAP = {
    'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    'md': "http://iec.ch/TC57/61970-552/ModelDescription/1#",
    'cim': "http://monitel.com/2021/schema-access#"
}

def setup_logger(csv_filename):
    """
    Создаёт и настраивает логгер для обработки конкретного CSV-файла.
    Лог-файл будет лежать в log/[имя_csv].log
    """
    log_dir = 'log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    basename = os.path.splitext(os.path.basename(csv_filename))[0]
    log_file = os.path.join(log_dir, f"{basename}.log")
    logger = logging.getLogger(basename)
    logger.setLevel(logging.INFO)
    # Очищаем старые хэндлеры (иначе при повторном вызове будут дубли)
    if logger.hasHandlers():
        logger.handlers.clear()
    fh = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger

# Запрашиваем у пользователя UID папки для ролей (универсальный на всю обработку)
folder_uid = input('Введите UID папки для ролей: ')

# Находим все .csv кроме Sample.csv (имя без учёта регистра)
csv_files = [
    f for f in os.listdir('.')
    if f.lower().endswith('.csv') and f.lower() != 'sample.csv'
]

if not csv_files:
    print("Не найдено csv-файлов для обработки (кроме Sample.csv).")
    exit()

# Для каждого подходящего csv-файла создаём свой xml и log
for csv_filename in csv_files:
    xml_filename = os.path.splitext(csv_filename)[0] + '.xml'
    logger = setup_logger(csv_filename)
    logger.info(f'Старт обработки файла {csv_filename} → {xml_filename}')

    try:
        # Создаём RDF-корневой тег
        rdf = etree.Element('{%s}RDF' % NSMAP['rdf'], nsmap=NSMAP)
        # Заголовок модели
        fullmodel = etree.SubElement(rdf, '{%s}FullModel' % NSMAP['md'], attrib={
            '{%s}about' % NSMAP['rdf']: '#_' + gen_uid()
        })
        time_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        etree.SubElement(fullmodel, '{%s}Model.created' % NSMAP['md']).text = time_str+"Z"
        etree.SubElement(fullmodel, '{%s}Model.version' % NSMAP['md']).text = "2025-03-04(11.7.1.7)"
        etree.SubElement(fullmodel, '{http://monitel.com/2014/schema-cim16#}Model.name').text = "Access"

        count = 0  # Считаем успешные строки

        # Открываем и парсим CSV-файл
        with open(csv_filename, encoding='utf-8') as csvfile:
            try:
                # Обрабатываем построчно через DictReader
                reader = csv.DictReader(csvfile, delimiter=';')
                for line_num, row in enumerate(reader, start=2):  # start=2 чтобы отчёт из логов соответствовал строкам (1 — шапка)
                    try:
                        # Извлекаем нужные поля (перехватит KeyError тоже!)
                        org_name = row['org_name']
                        dep_name = row['dep_name']
                        objectref_objectuid = row['dep_uid']

                        # Сгенерируем UIDs для ролей и связей
                        role_uid = gen_uid()
                        privilege_uid = gen_uid()
                        datagroup_uid = gen_uid()
                        objectref_uid = gen_uid()

                        logger.info(f'Строка {line_num}: Добавляется роль: {org_name}\\{dep_name}, dep_uid={objectref_objectuid}')
                        count += 1  # Увеличиваем счётчик успешно добавленных ролей

                        # -- Role --
                        role = etree.SubElement(rdf, '{%s}Role' % NSMAP['cim'], attrib={
                            '{%s}about' % NSMAP['rdf']: "#_"+role_uid
                        })
                        etree.SubElement(role, '{%s}IdentifiedObject.name' % NSMAP['cim']).text = f'Чтение записей под подр-ю {org_name}\\{dep_name}'
                        etree.SubElement(role, '{%s}IdentifiedObject.ParentObject' % NSMAP['cim'], attrib={
                            '{%s}resource' % NSMAP['rdf']: "#_"+folder_uid
                        })
                        etree.SubElement(role, '{%s}Role.isHost' % NSMAP['cim']).text = 'false'
                        etree.SubElement(role, '{%s}Role.isUser' % NSMAP['cim']).text = 'true'
                        etree.SubElement(role, '{%s}Role.kind' % NSMAP['cim'], attrib={
                            '{%s}resource' % NSMAP['rdf']: "cim:RoleKind.allow"
                        })
                        etree.SubElement(role, '{%s}Role.Privileges' % NSMAP['cim'], attrib={
                            '{%s}resource' % NSMAP['rdf']: "#_"+privilege_uid
                        })

                        # -- Privilege --
                        priv = etree.SubElement(rdf, '{%s}Privilege' % NSMAP['cim'], attrib={
                            '{%s}about' % NSMAP['rdf']: "#_"+privilege_uid
                        })
                        etree.SubElement(priv, '{%s}Privilege.Role' % NSMAP['cim'], attrib={
                            '{%s}resource' % NSMAP['rdf']: "#_"+role_uid
                        })
                        etree.SubElement(priv, '{%s}Privilege.DataItems' % NSMAP['cim'], attrib={
                            '{%s}resource' % NSMAP['rdf']: "#_"+datagroup_uid
                        })
                        etree.SubElement(priv, '{%s}Privilege.Operation' % NSMAP['cim'], attrib={
                            '{%s}resource' % NSMAP['rdf']: "#_2000065d-0000-0000-c000-0000006d746c"
                        })

                        # -- DataGroup --
                        datagr = etree.SubElement(rdf, '{%s}DataGroup' % NSMAP['cim'], attrib={
                            '{%s}about' % NSMAP['rdf']: "#_"+datagroup_uid
                        })
                        etree.SubElement(datagr, '{%s}IdentifiedObject.name' % NSMAP['cim']).text = f'{org_name}\\{dep_name}'
                        etree.SubElement(datagr, '{%s}IdentifiedObject.ParentObject' % NSMAP['cim'], attrib={
                            '{%s}resource' % NSMAP['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"
                        })
                        etree.SubElement(datagr, '{%s}DataItem.isHostRestricted' % NSMAP['cim']).text = 'false'
                        etree.SubElement(datagr, '{%s}DataItem.isUserRestricted' % NSMAP['cim']).text = 'true'
                        etree.SubElement(datagr, '{%s}DataItem.Privileges' % NSMAP['cim'], attrib={
                            '{%s}resource' % NSMAP['rdf']: "#_"+privilege_uid
                        })
                        etree.SubElement(datagr, '{%s}DataItem.Category' % NSMAP['cim'], attrib={
                            '{%s}resource' % NSMAP['rdf']: "#_20000db8-0000-0000-c000-0000006d746c"
                        })
                        etree.SubElement(datagr, '{%s}DataGroup.Class' % NSMAP['cim'], attrib={
                            '{%s}resource' % NSMAP['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"
                        })
                        etree.SubElement(datagr, '{%s}DataGroup.Objects' % NSMAP['cim'], attrib={
                            '{%s}resource' % NSMAP['rdf']: "#_"+objectref_uid
                        })

                        # -- ObjectReference --
                        oref = etree.SubElement(rdf, '{%s}ObjectReference' % NSMAP['cim'], attrib={
                            '{%s}about' % NSMAP['rdf']: "#_"+objectref_uid
                        })
                        etree.SubElement(oref, '{%s}ObjectReference.objectUid' % NSMAP['cim']).text = objectref_objectuid
                        etree.SubElement(oref, '{%s}ObjectReference.Group' % NSMAP['cim'], attrib={
                            '{%s}resource' % NSMAP['rdf']: "#_"+datagroup_uid
                        })
                    except Exception as e:
                        logger.error(f'Ошибка при обработке строки {line_num} в {csv_filename}: {e}')
            except Exception as e:
                logger.error(f'Ошибка чтения CSV-файла {csv_filename}: {e}')
    except Exception as e:
        logger.error(f'Критическая ошибка при подготовке XML для {csv_filename}: {e}')
        continue  # переходим к следующему файлу

    try:
        # Форматируем и сохраняем XML
        etree.indent(rdf, space="  ")
        xml_bytes = etree.tostring(rdf, xml_declaration=True, encoding='utf-8', pretty_print=True)
        with open(xml_filename, "wb") as f:
            f.write(xml_bytes)
        logger.info(f'Завершена обработка файла. Всего добавлено ролей: {count}. XML сохранён: {xml_filename}')
        print(f"Готово! {xml_filename} сформирован из {csv_filename}. Лог: log/{os.path.basename(os.path.splitext(csv_filename)[0])}.log")
    except Exception as e:
        logger.error(f'Ошибка записи XML-файла {xml_filename}: {e}')
