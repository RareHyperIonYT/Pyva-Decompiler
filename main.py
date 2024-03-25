import pprint
import io
import opcodes
import re
import sys
import argparse

from classreader import ClassReader

pp = pprint.PrettyPrinter()

def find_methods_by_name(clazz: dict, name: str):
    return [method for method in clazz['methods'] if clazz['constant_pool'][method['name_index'] - 1]['bytes'].decode('utf-8') == name]

def find_attributes_by_name(clazz: dict, attributes, name: str):
    return [attr for attr in attributes if clazz['constant_pool'][attr['attribute_name_index'] - 1]['bytes'].decode('utf-8') == name]

def parse_u1(f): return int.from_bytes(f.read(1), 'big')
def parse_u2(f): return int.from_bytes(f.read(2), 'big')
def parse_u4(f): return int.from_bytes(f.read(4), 'big')

def match_opcode(opcode, translations):
    for instruction, code in translations:
        if opcode == code:
            return instruction
    return opcode

def execute_code(clazz: dict, code: bytes):
    stack = []
    with io.BytesIO(code) as f:
        while f.tell() < len(code):
            opcode = parse_u1(f)

            if opcode == opcodes.GET_STATIC:
                index = parse_u2(f)

                fieldref = clazz['constant_pool'][index - 1]

                class_name = fieldref['class_name']
                field_name = fieldref['field_name']
                field_desc = fieldref['field_desc']

                stack.append({
                    'type': field_desc[1:][:-1]
                 })

                print(f"GETSTATIC {class_name}.{field_name} {field_desc}")
            elif opcode == opcodes.LDC:
                index = parse_u1(f)

                name = clazz['constant_pool'][clazz['constant_pool'][index - 1]['string_index'] - 1]['bytes'].decode('utf-8')

                stack.append({
                    'type': 'LDC', 'value': name
                })

                print(f"LDC \"{name}\"")
            elif opcode == opcodes.INVOKE_VIRTUAL:
                index = parse_u2(f)

                methodref = clazz['constant_pool'][index - 1]
                class_name = methodref['class_name']
                method_name = methodref['method_name']
                method_desc = methodref['method_desc']
                
                stack.append({ 'type': 'Invoke', 'method': method_name})

                print(f"INVOKEVIRTUAL {class_name}.{method_name}{method_desc}")
            elif opcode == opcodes.RETURN:
                print("RETURN")
            elif opcode == opcodes.BIPUSH:
                byte = parse_u1(f)
                print(f"BIPUSH {byte}")
                stack.append({ 'type': 'Integer', 'value': byte })
    print()
    print("Stack:", stack)
    print("Executed Code: ", end='')

    for i, obj in enumerate(stack):
        if obj['type'] == 'java/io/PrintStream':
            provided_string = stack[i + 1]['value']
            method = stack[i + 2]['method']

            if method == 'println':
                print(provided_string)


    assert False, "Executing code is not implemented yet."

def decompile_class(clazz: dict) -> str:
    lines = []
    lines.append("// Decompiled with Pyva Decompiler by RareHyperIonYT")
    lines.append(f"// Class Version: {clazz['major'] - 44}")
    
    class_line = ""

    class_type = "class"

    for access in clazz['access_flags']:
        if access == 'ACC_PUBLIC':
            class_line += 'public '
        elif access == 'ACC_STATIC':
            class_line += 'static '
        elif access == 'ACC_INTERFACE':
            class_type += 'interface '
        elif access == 'ACC_SYNTHETIC':
            class_line += '/* synthetic */ '
        elif access == 'ACC_ENUM':
            class_type += 'enum '

    class_line += f"{class_type} {clazz['name']}"

    if clazz['super_name'] != 'java/lang/Object':
        class_line += f" extends {clazz['super_name']}"

    if len(clazz['interfaces']) > 0:
        class_line += ' implements '
        for i, interface in enumerate(clazz['interfaces']):
            class_line += interface
            if i != 0 and i != len(clazz['interfaces'] - 1):
                class_line += ', '

    class_line += ' {'

    lines.append(class_line)
    lines.append('')

    for field in clazz['fields']:
        field_line = '    '
        for access in field['access_flags']:
            if access == 'ACC_PUBLIC':
                field_line += 'public '
            elif access == 'ACC_PRIVATE':
                field_line += 'private '
            elif access == 'ACC_PROTECTED':
                field_line += 'protected '
            elif access == 'ACC_FINAL':
                field_line += 'final '
            elif access == 'ACC_SYNTHETIC':
                field_line += '/* synthetic */ '
            elif access == 'ACC_ENUM':
                field_line += 'enum '
            elif access == 'ACC_VOLATILE':
                field_line += 'volatile '
            elif access == 'ACC_TRANSIENT':
                field_line += 'transient '
        
        field_desc = field['desc']
        field_line += field_desc
        field_line += f" {field['name']}"

        if len(field['attributes']) == 0:
            field_line += ';'
        else:
            field_line += ' = '
            for attribute in field['attributes']:
                if attribute['name'] == 'ConstantValue':
                    with io.BytesIO(attribute['info']) as f:
                        name_index = parse_u2(f)
                        constant = clazz['constant_pool'][name_index - 1]

                        if constant['tag'] == 'CONSTANT_Integer':
                            value = constant['bytes']

                            if value == 0:
                                field_line += 'false;'
                            elif value == 1:
                                field_line += 'true;'
                            else:
                                assert False, "Unexpected value for boolean: {constant}"
                        else:
                            assert False, f"We don't support constant {constant['tag']} for field decompilation yet."
                else:
                    assert False, f"We don't support attribute {attribute['name']} for field decompilation yet."
                
            
        lines.append(field_line)

    
    lines.append('')

    for method in clazz['methods']:
        method_line = '    '

        for access in method['access_flags']:
            if access == 'ACC_PUBLIC':
                method_line += 'public '
            elif access == 'ACC_PRIVATE':
                method_line += 'private '
            elif access == 'ACC_PROTECTED':
                method_line += 'protected '
            elif access == 'ACC_FINAL':
                method_line += 'final '
            elif access == 'ACC_SYNTHETIC':
                method_line += '/* synthetic */ '
            elif access == 'ACC_SYNCHRONIZED':
                method_line += 'synchronized '
            elif access == 'ACC_BRIDGE':
                method_line += '/* bridge */ '
            elif access == 'ACC_NATIVE':
                method_line += '/* native */ '
            elif access == 'ACC_ABSTRACT':
                method_line += 'abstract '
            elif access == 'ACC_STRICT':
                method_line += '/* strict */ '
            elif access == 'ACC_VARARGS':
                method_line += '/* varargs */ '
                

        args, return_type = method['desc']

        method_line += f"{return_type} "
        method_line += f"{method['name']}({', '.join(args)}) " + "{\n"
        
        for attribute in method['attributes']:
            name = attribute['name']

            if name == 'Code':
                tab = '        '
                code = attribute['info']['code']
                with io.BytesIO(code) as f:
                    while f.tell() < len(code):
                        opcode = parse_u1(f)


                        if opcode == opcodes.GET_STATIC:
                            index = parse_u2(f)

                            fieldref = clazz['constant_pool'][index - 1]

                            class_name = fieldref['class_name']
                            field_name = fieldref['field_name']
                            field_desc = fieldref['field_desc']



                            method_line += f"{tab}GETSTATIC {class_name}.{field_name} // RETURN: {field_desc}"
                        elif opcode == opcodes.LDC:
                            index = parse_u1(f)

                            name = clazz['constant_pool'][index - 1]['value']

                            method_line += f"{tab}LDC \"{name}\""
                        elif opcode == opcodes.INVOKE_VIRTUAL:
                            index = parse_u2(f)

                            methodref = clazz['constant_pool'][index - 1]
                            class_name = methodref['class_name']
                            method_name = methodref['method_name']
                            method_desc = methodref['method_desc']

                            method_line += f"{tab}INVOKEVIRTUAL {class_name}.{method_name}{method_desc}"
                        elif opcode == opcodes.INVOKE_SPECIAL:
                            index = parse_u2(f)

                            methodref = clazz['constant_pool'][index - 1]
                            class_name = methodref['class_name']
                            method_name = methodref['method_name']
                            method_desc = methodref['method_desc']

                            method_line += f"{tab}INVOKESPECIAL {class_name}.{method_name}{method_desc}"
                        elif opcode == opcodes.ICONST_0:
                            method_line += f"{tab}ICONST_0"
                        elif opcode == opcodes.ICONST_1:
                            method_line += f"{tab}ICONST_1"
                        elif opcode == opcodes.ICONST_2:
                            method_line += f"{tab}ICONST_2"
                        elif opcode == opcodes.ICONST_3:
                            method_line += f"{tab}ICONST_3"
                        elif opcode == opcodes.ICONST_4:
                            method_line += f"{tab}ICONST_4"
                        elif opcode == opcodes.PUTFIELD:
                            index = parse_u2(f)
                            fieldref = clazz['constant_pool'][index - 1]
                            class_name = fieldref['class_name']
                            field_name = fieldref['field_name']

                            method_line += f"{tab}PUTFIELD {index} // Field: {class_name}.{field_name}"
                        elif opcode == opcodes.NEW_ARRAY:
                            type = parse_u1(f)
                            if type == 4: type = 'boolean'
                            elif type == 5: type = 'char'
                            elif type == 6: type = 'float'
                            elif type == 7: type = 'double'
                            elif type == 8: type = 'byte'
                            elif type == 9: type = 'short'
                            elif type == 10: type = 'int'
                            elif type == 11: type = 'long'
                            else: type = 'unknown'
                            method_line += f"{tab}NEWARRAY // Type: {type}"
                        elif opcode == opcodes.DUP:
                            method_line += f"{tab}DUP"
                        elif opcode == opcodes.ICONST_3:
                            method_line += f"{tab}ICONST_3"
                        elif opcode == opcodes.BASTORE:
                            method_line += f"{tab}BASTORE"
                        elif opcode == opcodes.RETURN:
                            method_line += f"{tab}RETURN"
                        elif opcode == opcodes.ARETURN:
                            method_line += f"{tab}ARETURN"
                        elif opcode == opcodes.ALOAD_0:
                            method_line += f"{tab}ALOAD_0"
                        else:
                            method_line += f'{tab}{opcode}'

                        method_line += '\n' if f.tell() < len(code) else ''
                            
                        #else:
                            #assert False, f"We do not support opcode {opcode} for decompilation yet."
                            


        

        method_line += '\n    }\n'
        lines.append(method_line)

    lines.append('')
    lines.append('}')

    return lines

def parse_class(file_path):
    with open(file_path, "rb") as f:
        classReader = ClassReader(f.read())
        clazz = classReader.read()
        clazz = classReader.clean(clazz)
        return clazz



parser = argparse.ArgumentParser(description="Process some arguments.")
    

parser.add_argument(
    "-input",
    dest="input_file",
    required=True,
    help="Path to the class file."
)

parser.add_argument(
    "-debug",
    dest="debug",
    default=False,
    action="store_true",
    help="Enable debug mode. (true/false)"
)

args = parser.parse_args()

input_file = args.input_file
debug_mode = args.debug

clazz = parse_class(input_file)
result = decompile_class(clazz)

if debug_mode:
    pp.pprint(clazz)
else:
    print()
    print('\n'.join(result))
