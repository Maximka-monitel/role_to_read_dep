"""
Модуль генерации XML файлов в формате RDF
Масштабируемый для любого проекта
"""

import uuid
from datetime import datetime
from lxml import etree
from lxml.etree import xmlfile
from typing import Dict, List, Set, Any, Callable
from .config_manager import get_config_value

def gen_uid() -> str:
    """Генерирует уникальный идентификатор."""
    return str(uuid.uuid4())


class XMLGenerator:
    """Генератор XML файлов с настраиваемыми параметрами."""
    
    def __init__(self, namespaces: Dict[str, str] = None):
        """
        Инициализация генератора XML.
        
        Args:
            namespaces: словарь пространств имен {prefix: uri}
        """
        self.namespaces = get_config_value('xml_generation.namespaces')
        self.default_model_version = "1.0.0"
        self.default_model_name = "GeneratedModel"
    
    def generate_xml(
        self,
        output_file: str,
        content_generator: Callable,
        encoding: str = 'utf-8'
    ) -> None:
        """
        Генерирует XML файл используя переданный генератор контента.
        
        Args:
            output_file: путь к выходному файлу
            content_generator: функция-генератор контента
            encoding: кодировка файла
        """
        with xmlfile(output_file, encoding=encoding) as xf:
            with xf.element('{%s}RDF' % self.namespaces['rdf'], nsmap=self.namespaces):
                content_generator(xf)
    
    def add_full_model(
        self, 
        xf: xmlfile, 
        model_version: str = None, 
        model_name: str = None,
        additional_elements: List[Dict] = None
    ) -> str:
        """
        Добавляет элемент FullModel с метаданными.
        
        Args:
            xf: объект xmlfile
            model_version: версия модели
            model_name: имя модели
            additional_elements: дополнительные элементы
            
        Returns:
            str: UID созданной модели
        """
        model_uid = gen_uid()
        model_version = model_version or self.default_model_version
        model_name = model_name or self.default_model_name
        
        with xf.element('{%s}FullModel' % self.namespaces.get('md', ''), 
                       attrib={'{%s}about' % self.namespaces['rdf']: '#_' + model_uid}):
            time_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            xf.write(etree.Element('{%s}Model.created' % self.namespaces.get('md', ''), 
                                 text=time_str + "Z"))
            xf.write(etree.Element('{%s}Model.version' % self.namespaces.get('md', ''), 
                                 text=model_version))
            xf.write(etree.Element('{%s}Model.name' % self.namespaces.get('md', ''), 
                                 text=model_name))
            
            # Добавляем дополнительные элементы если указаны
            if additional_elements:
                for elem in additional_elements:
                    ns = elem.get('namespace', 'md')
                    xf.write(etree.Element('{%s}%s' % (self.namespaces.get(ns, ''), elem['name']), 
                                         text=elem.get('text', ''),
                                         attrib=elem.get('attributes', {})))
        
        return model_uid
    
    def add_custom_element(
        self,
        xf: xmlfile,
        element_name: str,
        namespace: str,
        attributes: Dict[str, str] = None,
        text: str = None,
        child_elements: List[Dict] = None
    ) -> None:
        """
        Добавляет пользовательский элемент XML.
        
        Args:
            xf: объект xmlfile
            element_name: имя элемента
            namespace: префикс пространства имен
            attributes: атрибуты элемента
            text: текстовое содержимое
            child_elements: дочерние элементы
        """
        ns_uri = self.namespaces.get(namespace, '')
        attrib = attributes or {}
        
        if child_elements:
            with xf.element('{%s}%s' % (ns_uri, element_name), attrib=attrib):
                if text:
                    xf.write(etree.Element('{%s}text' % ns_uri, text=text))
                for child in child_elements:
                    self.add_custom_element(
                        xf, child['name'], child['namespace'],
                        child.get('attributes'), child.get('text'),
                        child.get('child_elements')
                    )
        else:
            element = etree.Element('{%s}%s' % (ns_uri, element_name), attrib=attrib)
            if text:
                element.text = text
            xf.write(element)


class AccessXMLGenerator(XMLGenerator):
    """Специализированный генератор XML для системы доступа."""
    
    def __init__(self):
        """Инициализация генератора для системы доступа."""
        super().__init__({
            'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            'md': "http://iec.ch/TC57/61970-552/ModelDescription/1#",
            'cim': "http://monitel.com/2021/schema-access#"
        })
    
    def add_data_group(
        self,
        xf: xmlfile,
        group_uid: str,
        group_name: str,
        parent_uid: str = None,
        additional_attributes: Dict = None
    ) -> str:
        """
        Добавляет элемент DataGroup.
        
        Args:
            xf: объект xmlfile
            group_uid: UID группы
            group_name: имя группы
            parent_uid: UID родительской группы
            additional_attributes: дополнительные атрибуты
            
        Returns:
            str: UID созданной группы данных
        """
        data_group_uid = group_uid or gen_uid()
        attrib = {'{%s}about' % self.namespaces['rdf']: "#_" + data_group_uid}
        
        with xf.element('{%s}DataGroup' % self.namespaces['cim'], attrib=attrib):
            xf.write(etree.Element('{%s}IdentifiedObject.name' % self.namespaces['cim'], 
                                 text=group_name))
            
            if parent_uid:
                xf.write(etree.Element('{%s}IdentifiedObject.ParentObject' % self.namespaces['cim'], 
                                     attrib={'{%s}resource' % self.namespaces['rdf']: "#_" + parent_uid}))
            
            # Добавляем стандартные атрибуты
            xf.write(etree.Element('{%s}DataItem.isHostRestricted' % self.namespaces['cim'], 
                                 text='false'))
            xf.write(etree.Element('{%s}DataItem.isUserRestricted' % self.namespaces['cim'], 
                                 text='true'))
            
            # Добавляем дополнительные атрибуты если указаны
            if additional_attributes:
                for key, value in additional_attributes.items():
                    xf.write(etree.Element('{%s}%s' % (self.namespaces['cim'], key), text=value))
        
        return data_group_uid
    
    def add_role_with_privilege(
        self,
        xf: xmlfile,
        role_name: str,
        parent_uid: str,
        data_items_uids: List[str],
        operation_uid: str = "#_2000065d-0000-0000-c000-0000006d746c",
        role_kind: str = "cim:RoleKind.allow"
    ) -> None:
        """
        Добавляет роль с привилегиями.
        
        Args:
            xf: объект xmlfile
            role_name: имя роли
            parent_uid: UID родительского объекта
            data_items_uids: список UID элементов данных
            operation_uid: UID операции
            role_kind: тип роли
        """
        role_uid = gen_uid()
        privilege_uid = gen_uid()
        
        # Добавляем роль
        with xf.element('{%s}Role' % self.namespaces['cim'], 
                       attrib={'{%s}about' % self.namespaces['rdf']: "#_" + role_uid}):
            xf.write(etree.Element('{%s}IdentifiedObject.name' % self.namespaces['cim'], 
                                 text=role_name))
            xf.write(etree.Element('{%s}IdentifiedObject.ParentObject' % self.namespaces['cim'], 
                                 attrib={'{%s}resource' % self.namespaces['rdf']: "#_" + parent_uid}))
            xf.write(etree.Element('{%s}Role.isHost' % self.namespaces['cim'], text='false'))
            xf.write(etree.Element('{%s}Role.isUser' % self.namespaces['cim'], text='true'))
            xf.write(etree.Element('{%s}Role.kind' % self.namespaces['cim'], 
                                 attrib={'{%s}resource' % self.namespaces['rdf']: role_kind}))
            xf.write(etree.Element('{%s}Role.Privileges' % self.namespaces['cim'], 
                                 attrib={'{%s}resource' % self.namespaces['rdf']: "#_" + privilege_uid}))
        
        # Добавляем привилегию
        with xf.element('{%s}Privilege' % self.namespaces['cim'], 
                       attrib={'{%s}about' % self.namespaces['rdf']: "#_" + privilege_uid}):
            xf.write(etree.Element('{%s}Privilege.Role' % self.namespaces['cim'], 
                                 attrib={'{%s}resource' % self.namespaces['rdf']: "#_" + role_uid}))
            
            # Добавляем ссылки на элементы данных
            for item_uid in data_items_uids:
                xf.write(etree.Element('{%s}Privilege.DataItems' % self.namespaces['cim'], 
                                     attrib={'{%s}resource' % self.namespaces['rdf']: "#_" + item_uid}))
            
            xf.write(etree.Element('{%s}Privilege.Operation' % self.namespaces['cim'], 
                                 attrib={'{%s}resource' % self.namespaces['rdf']: operation_uid}))


# Фабричные функции для обратной совместимости
def create_access_generator() -> AccessXMLGenerator:
    """Создает генератор для системы доступа."""
    return AccessXMLGenerator()


def create_custom_generator(namespaces: Dict[str, str]) -> XMLGenerator:
    """Создает кастомный генератор XML."""
    return XMLGenerator(namespaces)