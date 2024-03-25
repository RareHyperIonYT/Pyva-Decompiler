import access_flags
import opcodes
import io
import re

def parse_u1(f): return int.from_bytes(f.read(1), 'big')
def parse_u2(f): return int.from_bytes(f.read(2), 'big')
def parse_u4(f): return int.from_bytes(f.read(4), 'big')

def parse_flags(value: int, flags: [(str, int)]) -> [str]:
    return [name for (name, mask) in flags if (value & mask) != 0]

def parse_field_descriptor(desc: str) -> str:
    if desc == 'Z':
        return 'boolean'
    else:
        return desc[1:][:-1]

def parse_attributes(f, count):
    attributes = []
    for i in range(count):
        attribute = {}
        attribute['attribute_name_index'] = parse_u2(f)
        attribute_length = parse_u4(f)
        attribute['info'] = f.read(attribute_length)
        attributes.append(attribute)
    return attributes

def parse_code_info(info: bytes) -> dict:
    code = {}
    with io.BytesIO(info) as f:
        code['max_stack'] = parse_u2(f)
        code['max_locals'] = parse_u2(f)
        code_length = parse_u4(f)
        code['code'] = f.read(code_length)
        exception_table_length = parse_u2(f)
        exceptions = []

        for i in range(exception_table_length):
            exception = {}
            exception['start_pc'] = parse_u2(f)
            exception['end_pc'] = parse_u2(f)
            exception['handler_pc'] = parse_u2(f)
            exception['catch_type'] = parse_u2(f)
            exceptions.append(exception)
        
        code['exception_table'] = exceptions
        
        attributes_count = parse_u2(f)
        code['attributes'] = parse_attributes(f, attributes_count)

    return code
    
def translate(type: str) -> str:
    if type == 'Z': return 'boolean'
    elif type == 'B': return 'byte'
    elif type == 'C': return 'char'
    elif type == 'D': return 'double'
    elif type == 'F': return 'float'
    elif type == 'I': return 'int'
    elif type == 'J': return 'long'
    elif type == 'S': return 'short'
    elif type == 'V': return 'void'
    elif type == 'Z[]': return 'boolean[]'
    elif type == 'B[]': return 'byte[]'
    elif type == 'C[]': return 'char[]'
    elif type == 'D[]': return 'double[]'
    elif type == 'F[]': return 'float[]'
    elif type == 'I[]': return 'int[]'
    elif type == 'J[]': return 'long[]'
    elif type == 'S[]': return 'short[]'
    else: return type
    

def format_descriptor(desc: tuple) -> tuple:
    args, return_type = desc

    for i, arg in enumerate(args):
        args[i] = translate(arg)

    return_type = translate(return_type)

    return args, return_type

def parse_descriptor_old(desc: str) -> tuple:
    match = re.match(r"\(([^)]*)\)(.*)", desc)
    
    if match:
        args_str = match.group(1)
        args = [arg.strip("L")[:-1] if arg.startswith("L") else arg for arg in re.findall(r"([ZBCDFIJSV]|L[^;]+;)", args_str)]
        return_type = match.group(2).strip()

        return format_descriptor((args, return_type))
    else:
        return None
    
def parse_descriptor(desc: str) -> tuple:
    match = re.match(r"\(([^)]*)\)(.*)", desc)
    
    if match:
        args_str = match.group(1)
        args = []
        for arg in re.findall(r"(\[?[ZBCDFIJSV]|L[^;]+;|\[L[^;]+;)", args_str):
            if arg.startswith("L"):
                arg = arg.strip("L")[:-1]
            
            if arg.startswith("[L"):
                arg = "[" + arg[2:-1]

            if arg.startswith("["):
                arg = arg[1:] + "[]"
            
            args.append(arg)

        return_type = match.group(2).strip()

        if return_type.startswith("L"):
            return_type = return_type.strip("L")[:-1]
            
        if return_type.startswith("[L"):
            return_type = "[" + return_type[2:-1]

        if return_type.startswith("["):
            return_type = return_type[1:] + "[]"

        return format_descriptor((args, return_type))
    else:
        return None

def parse_field_descriptor(desc: str) -> str:
    args = desc.strip("L")[:-1] if desc.startswith("L") else translate(desc)
    return args
    
class ClassReader():
    def __init__(self, class_bytes):
        self.class_bytes = class_bytes
    
    def read(self) -> dict:
        clazz = {}
        with io.BytesIO(self.class_bytes) as f:
            clazz['magic'] = hex(parse_u4(f))[2:].upper()
            clazz['minor'] = parse_u2(f)
            clazz['major'] = parse_u2(f)

            constant_pool_size = parse_u2(f)
            constant_pool = []

            for i in range(constant_pool_size-1):
                cp_info = {}
                tag = parse_u1(f)
        
                if tag == opcodes.CONSTANT_Methodref:
                    cp_info['tag'] = 'CONSTANT_Methodref'
                    cp_info['class_index'] = parse_u2(f)
                    cp_info['name_and_type_index'] = parse_u2(f)
                elif tag == opcodes.CONSTANT_InterfaceMethodRef:
                    cp_info['tag'] = 'CONSTANT_InterfaceMethodRef'
                    cp_info['class_index'] = parse_u2(f)
                    cp_info['name_and_type_index'] = parse_u2(f)
                elif tag == opcodes.CONSTANT_MethodType:
                    cp_info['tag'] = 'CONSTANT_MethodType'
                    cp_info['descriptor_index'] = parse_u2(f)
                elif tag == opcodes.CONSTANT_MethodHandle:
                    cp_info['tag'] = 'CONSTANT_MethodHandle'
                    cp_info['reference_kind'] = parse_u1(f)
                    cp_info['reference_index'] = parse_u2(f)
                elif tag == opcodes.CONSTANT_InvokeDynamic:
                    cp_info['tag'] = 'CONSTANT_InvokeDynamic'
                    cp_info['bootstrap_method_attr_index'] = parse_u2(f)
                    cp_info['name_and_type_index'] = parse_u2(f)
                elif tag == opcodes.CONSTANT_Class:
                    cp_info['tag'] = 'CONSTANT_Class'
                    cp_info['name_index'] = parse_u2(f)
                elif tag == opcodes.CONSTANT_NameAndType:
                    cp_info['tag'] = 'CONSTANT_NameAndType'
                    cp_info['name_index'] = parse_u2(f)
                    cp_info['descriptor_index'] = parse_u2(f)
                elif tag == opcodes.CONSTANT_Utf8:
                    cp_info['tag'] = 'CONSTANT_Utf8'
                    length = parse_u2(f)
                    cp_info['bytes'] = f.read(length)
                elif tag == opcodes.CONSTANT_Integer:
                    cp_info['tag'] = 'CONSTANT_Integer'
                    cp_info['bytes'] = parse_u4(f)
                elif tag == opcodes.CONSTANT_Long:
                    cp_info['tag'] = 'CONSTANT_Long'
                    cp_info['bytes'] = parse_u4(f)
                elif tag == opcodes.CONSTANT_Fieldref:
                    cp_info['tag'] = 'CONSTANT_Fieldref'
                    cp_info['class_index'] = parse_u2(f)
                    cp_info['name_and_type_index'] = parse_u2(f)
                elif tag == opcodes.CONSTANT_String:
                    cp_info['tag'] = 'CONSTANT_String'
                    cp_info['string_index'] = parse_u2(f)
                elif tag == 0:
                    cp_info['tag'] = 'CONSTANT_Utf8'
                    cp_info['bytes'] = f.read(3)
                else:
                    f.read(0)
                    assert False, f"Unexpected tag {tag}"
    
                constant_pool.append(cp_info)

            clazz['constant_pool'] = constant_pool
            clazz['access_flags'] = parse_flags(parse_u2(f), access_flags.class_access_flags)
            clazz['this_class'] = parse_u2(f)
            clazz['super_class'] = parse_u2(f)
            
            # CLASS NAME -> pp.pprint(clazz['constant_pool'][clazz['constant_pool'][clazz['this_class'] - 1]['name_index'] -1])
            # SUPER CLASS NAME -> pp.pprint(clazz['constant_pool'][clazz['constant_pool'][clazz['super_class'] - 1]['name_index'] -1])

            interfaces_count = parse_u2(f)
            interfaces = []

            for i in range(interfaces_count):
                interfaces.append(parse_u2(f))
            
            clazz['interfaces'] = interfaces

            fields_count = parse_u2(f)
            fields = []

            for i in range(fields_count):
                field = {}
                field['access_flags'] = parse_flags(parse_u2(f), access_flags.field_access_flags)
                field['name_index'] = parse_u2(f)
                field['descriptor_index'] = parse_u2(f)
                attributes_count = parse_u2(f)
                field['attributes'] = parse_attributes(f, attributes_count)
                fields.append(field)
                

            clazz['fields'] = fields

            methods_count = parse_u2(f)
            methods = []


            for i in range(methods_count):
                method = {}
                method['access_flags'] = parse_flags(parse_u2(f), access_flags.method_access_flags)
                method['name_index'] = parse_u2(f)
                method['descriptor_index'] = parse_u2(f)

                # METHOD NAME -> pp.pprint(clazz['constant_pool'][method['name_index'] -1])
                # METHOD DESCRIPTOR -> pp.pprint(clazz['constant_pool'][method['descriptor_index'] -1])

                attributes_count = parse_u2(f)

                method['attributes'] = parse_attributes(f, attributes_count)
                methods.append(method)

            clazz['methods'] = methods

            attributes_count = parse_u2(f)
            clazz['attributes'] = parse_attributes(f, attributes_count)
        
        return clazz
    
    def clean(self, clazz: dict) -> dict:
        class_name_index = clazz['this_class']
        clazz.pop('this_class')
        clazz['name'] = clazz['constant_pool'][clazz['constant_pool'][class_name_index - 1]['name_index'] -1]['bytes'].decode('utf-8')
        super_name_index = clazz['super_class']
        clazz.pop('super_class')
        clazz['super_name'] = clazz['constant_pool'][clazz['constant_pool'][super_name_index - 1]['name_index'] -1]['bytes'].decode('utf-8')

        constant_pool = clazz['constant_pool']

        for constant in constant_pool:
            tag = constant['tag']

            if tag == 'CONSTANT_String':

                try:
                    constant['value'] = constant_pool[constant['string_index'] - 1]['bytes'].decode('utf-8')
                    constant.pop('string_index')
                except:
                    constant['value'] = constant_pool[constant['string_index'] - 1]['bytes']
                    constant.pop('string_index')
                #print('\n', constant)
            elif tag == 'CONSTANT_Class':
                name_index = constant['name_index']
                constant['name'] = constant_pool[name_index - 1]['bytes'].decode('utf-8')
                constant.pop('name_index')

        for constant in constant_pool:
            tag = constant['tag']

            if tag == 'CONSTANT_Methodref':
                class_index = constant['class_index']
                class_name = constant_pool[class_index-1]['name']

                name_and_type_index = constant['name_and_type_index']
                name_index = constant_pool[name_and_type_index-1]['name_index']
                descriptor_index = constant_pool[name_and_type_index-1]['descriptor_index']

                method_name = constant_pool[name_index-1]['bytes'].decode('utf-8')
                method_desc = constant_pool[descriptor_index-1]['bytes'].decode('utf-8')

                constant.pop('class_index')
                constant.pop('name_and_type_index')

                constant['class_name'] = class_name
                constant['method_name'] = method_name
                constant['method_desc'] = method_desc
            elif tag == 'CONSTANT_Fieldref':
                class_index = constant['class_index']
                name_and_type_index = constant['name_and_type_index']

                class_name = constant_pool[class_index - 1]['name']

                name_index = constant_pool[name_and_type_index-1]['name_index']
                descriptor_index = constant_pool[name_and_type_index-1]['descriptor_index']

                field_name = constant_pool[name_index-1]['bytes'].decode('utf-8')
                field_desc = constant_pool[descriptor_index-1]['bytes'].decode('utf-8')

                constant.pop('class_index')
                constant.pop('name_and_type_index')

                constant['class_name'] = class_name
                constant['field_name'] = field_name
                constant['field_desc'] = field_desc
                
        
        clazz['constant_pool'] = constant_pool

        interfaces = clazz['interfaces']

        for i, interface in enumerate(interfaces):
            interfaces[i] = constant_pool[interface - 1]['name']


        fields = clazz['fields']

        for field in fields:
            name_index = field['name_index']
            descriptor_index = field['descriptor_index']
            field['name'] = constant_pool[name_index - 1]['bytes'].decode('utf-8')
            descriptor = constant_pool[descriptor_index - 1]['bytes'].decode('utf-8')
            
            return_type = parse_field_descriptor(descriptor)

            field['desc'] = return_type
            field.pop('name_index')
            field.pop('descriptor_index')

            attributes = field['attributes']

            for attribute in attributes:
                attribute_name_index = attribute['attribute_name_index']
                attribute['name'] = constant_pool[attribute_name_index - 1]['bytes'].decode('utf-8')
                attribute.pop('attribute_name_index')
        
        methods = clazz['methods']

        for method in methods:
            name_index = method['name_index']
            descriptor_index = method['descriptor_index']
            method.pop('name_index')
            method.pop('descriptor_index')

            descriptor = constant_pool[descriptor_index - 1]['bytes'].decode('utf-8')
            method['name'] = constant_pool[name_index - 1]['bytes'].decode('utf-8')
            args, return_type = parse_descriptor(descriptor)
            method['desc'] = (args, return_type)

            attributes = method['attributes']

            for attribute in attributes:
                attribute_name_index = attribute['attribute_name_index']
                attribute['name'] = constant_pool[attribute_name_index - 1]['bytes'].decode('utf-8')
                attribute.pop('attribute_name_index')

                if attribute['name'] == 'Code':
                    attribute['info'] = parse_code_info(attribute['info'])
    
    
            method['attributes'] = attributes

        return clazz