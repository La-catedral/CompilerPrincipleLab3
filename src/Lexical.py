#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author  : Jingshuo Liu
# @File    : Lexical.py
import sys



# create list for the fixed keywords、separators and operators
class Lexer:

    row_num = 0  # current line number
    col_num = 0  # pointer that point to next char

    octal_set = {str(val) for val in range(8)}  # octal char set

    hexad_set = {str(val) for val in range(10)} | \
                {chr(val) for val in range(ord("A"), ord("F") + 1)} | \
                {chr(val) for val in range(ord("a"), ord("f") + 1)}  # hexadecimal char set

    # decim_set is useless for there already have function isdigit()

    KEYWORD = [
        'auto', 'short', 'int', 'long', 'float', 'bool', 'double', 'char', 'struct','not','and','or'
        'union', 'enum', 'typedef', 'const', 'unsigned', 'signed', 'extern', 'register','true','false',
        'static', 'volatile', 'void',	'if', 'then', 'else', 'switch', 'case', 'for', 'do', 'while',
        'goto', 'continue', 'break', 'default', 'sizeof', 'return', 'call', 'proc', 'prog', 'param']

    SEPARATOR = ['{', '}', '[', ']', '(', ')', '~', ',', ';', '.', '?', ':', ' ']

    OPERATOR = ['+', '++', '-', '--', '+=', '-=', '*', '*=', '%', '%=', '->', '|', '||', '|=',
                '/', '/=', '>', '<', '>=', '<=', '=', '==', '!=', '!', '&']

    specie_dic = {}  # store the species code of keywords 、separators and operators
    signal_dic = {}  # store the attribute of id

    def __init__(self):
        i = 257  # start out of ascii
        for keyword in self.KEYWORD:
            self.specie_dic[keyword] = i
            i += 1
        for separator in self.SEPARATOR:
            self.specie_dic[separator] = i
            i += 1
        for opr in self.OPERATOR:
            self.specie_dic[opr] = i
            i += 1

    def getchar(self, buffer):
        """
        read and return a character from the specific location
        of buffer,or EOF if no more to read
        :param buffer:
        :return:
        """
        if self.col_num >= len(buffer[self.row_num]):
            self.row_num += 1
            self.col_num = 0
        if self.row_num == len(buffer):
            return 'EOF'
        else:
            while len(buffer[self.row_num]) == 0:  # skip blank line
                self.row_num += 1
            char = buffer[self.row_num][self.col_num]
            self.col_num += 1
            return char

    def retract(self, buffer):
        """
        retract the pointer to the next character of buffer
        :param buffer: input stream,in format of list
        :return: None
        """
        if self.col_num > 0:
            self.col_num = self.col_num - 1
        else:
            self.row_num -= 1
            self.col_num = len(buffer[self.row_num]) - 1
        return

    def error_handle(self, msg="Illegal character.",line_num=0):
        """
        Print error information to standard output
        :return:None
        """
        line_num = self.row_num if line_num == 0 else line_num
        if self.col_num == 0:
            print("Lexical error at Line " + str(line_num) + ": " + msg)
        else:
            print("Lexical error at Line " + str(line_num + 1) + ": " + msg)
        return

    def scanner(self, buffer):
        """
        scan the input character stream and tokenize them using the DFG
        already designed for the object programing language
        :return: string consist of token units split with \n
        """
        # read the characters from the input sequentially，each iteration generate a token
        tokens = ""  # the buffer to store the result
        # like "while".ljust(10) + "<" +"WHILE".center(7)+","+"_".center(7)+">\n"
        break_flag = False
        new_char = self.getchar(buffer)

        classes,attris,line_nums = [],[],[]

        while new_char != 'EOF':
            if new_char.strip() == '':  # skip tab or blank
                pass
            elif new_char.isalpha() or new_char == '_':  # may be the keyword or id
                word = ''
                line_num = self.row_num
                while new_char.isalpha() or new_char.isdigit() or new_char == '_':
                    word += new_char
                    new_char = self.getchar(buffer)
                    if new_char == 'EOF':
                        break_flag = True
                self.retract(buffer)
                if word in self.KEYWORD:
                    tokens += word.ljust(10) + "<" + word.upper().center(7) + "," + '_'.center(
                        7) + ">\n"
                    classes.append(word.lower())
                    attris.append('_')
                    line_nums.append(line_num)

                else:
                    tokens += word.ljust(10) + "<" + "IDN".center(7) + "," + word.center(
                        7) + ">\n"  # use the value of the id itself as attribute value
                    self.signal_dic[word] = len(self.signal_dic) if word not in self.signal_dic.keys() else self.signal_dic[word] # add the identifier to signal dic
                    classes.append('id')
                    attris.append(word.lower())
                    line_nums.append(line_num)
                if break_flag:  # EOF break
                    break

            elif new_char.isdigit() or new_char == '.':  # float or integer(octal or decimal or hexadecimal)
                number = ''
                line_num = self.row_num
                if new_char == '0':  # enter state 7
                    number += new_char
                    new_char = self.getchar(buffer)
                    if new_char == 'x' or new_char == "X":  # enter state 8,hexadecimal
                        number += new_char
                        new_char = self.getchar(buffer)
                        if new_char not in self.hexad_set:
                            self.retract(buffer)
                            self.error_handle("illegal hexadecimal.")
                        else:
                            while new_char in self.hexad_set:
                                number += new_char
                                new_char = self.getchar(buffer)
                            self.retract(buffer)
                            tokens += number.ljust(10) + "<" + "hexadecimal".upper().center(7) + "," + number.center(
                                7) + ">\n"
                            classes.append('hex')
                            attris.append(number)
                            line_nums.append(line_num)
                    elif new_char in self.octal_set:  # enter state 1,recognize octal
                        number += new_char
                        new_char = self.getchar(buffer)
                        while new_char in self.octal_set:
                            number += new_char
                            new_char = self.getchar(buffer)
                        self.retract(buffer)
                        tokens += number.ljust(10) + "<" + "octal".upper().center(7) + "," + number.center(
                            7) + ">\n"
                        classes.append('oct')
                        attris.append(number)
                        line_nums.append(line_num)
                    elif new_char == '.':  # enter state 2
                        number += new_char
                        new_char = self.getchar(buffer)
                        if new_char.isdigit():  # enter state 2
                            while new_char.isdigit():  # stay in state 2
                                number += new_char
                                new_char = self.getchar(buffer)
                            if new_char in {'e', 'E'}:  # enter state 4
                                number += new_char
                                new_char = self.getchar(buffer)
                                if new_char in {'+', '-'}:
                                    number += new_char
                                    new_char = self.getchar(buffer)
                                elif not new_char.isdigit():
                                    self.retract(buffer)
                                    self.error_handle('float unclosed.')
                                    continue

                                while new_char.isdigit():
                                    number += new_char
                                    new_char = self.getchar(buffer)
                                self.retract(buffer)
                                tokens += number.ljust(10) + "<" + "float".upper().center(7) + "," + number.center(
                                    7) + ">\n"
                                classes.append('const_float')
                                attris.append(number)
                                line_nums.append(line_num)
                            else:
                                self.retract(buffer)
                                tokens += number.ljust(10) + "<" + "float".upper().center(7) + "," + number.center(
                                    7) + ">\n"
                                classes.append('const_float')
                                attris.append(number)
                                line_nums.append(line_num)
                        else:
                            self.retract(buffer)
                            self.error_handle("float unclosed")
                    else:  # just 0
                        self.retract(buffer)
                        tokens += number.ljust(10) + "<" + "NUMBER".center(7) + "," + number.center(
                            7) + ">\n"
                        classes.append('dec')
                        attris.append(number)
                        line_nums.append(line_num)
                        if new_char == 'EOF':
                            break
                else:  # consider integer start with number [1-9] or a float
                    if new_char == '.':  # enter state 3
                        number += new_char
                        new_char = self.getchar(buffer)
                        if not new_char.isdigit():
                            self.retract(buffer)
                            self.error_handle('float unclosed.')
                        else:  # enter state 2
                            number += new_char
                            new_char = self.getchar(buffer)
                            while new_char.isdigit():  # stay in state 2
                                number += new_char
                                new_char = self.getchar(buffer)
                            if new_char in {'e', 'E'}:  # enter state 4
                                number += new_char
                                new_char = self.getchar(buffer)
                                if new_char in {'+', '-'}:
                                    number += new_char
                                    new_char = self.getchar(buffer)
                                elif not new_char.isdigit():
                                    self.retract(buffer)
                                    self.error_handle('float unclosed.')
                                    continue
                                while new_char.isdigit():
                                    number += new_char
                                    new_char = self.getchar(buffer)
                                self.retract(buffer)
                                tokens += number.ljust(10) + "<" + "float".upper().center(7) + "," + number.center(
                                    7) + ">\n"
                                classes.append('const_float')
                                attris.append(number)
                                line_nums.append(line_num)
                            else:
                                self.retract(buffer)
                                tokens += number.ljust(10) + "<" + "float".upper().center(7) + "," + number.center(
                                    7) + ">\n"
                                classes.append('const_float')
                                attris.append(number)
                                line_nums.append(line_num)
                    else:  # enter state 1
                        number += new_char
                        new_char = self.getchar(buffer)
                        while new_char.isdigit():
                            number += new_char
                            new_char = self.getchar(buffer)
                        if new_char == '.':
                            number += new_char
                            new_char = self.getchar(buffer)
                            while new_char.isdigit():  # stay in state 2
                                number += new_char
                                new_char = self.getchar(buffer)
                            if new_char in {'e', 'E'}:  # enter state 4
                                number += new_char
                                new_char = self.getchar(buffer)
                                if new_char in {'+', '-'}:
                                    number += new_char
                                    new_char = self.getchar(buffer)
                                elif not new_char.isdigit():
                                    self.retract(buffer)
                                    self.error_handle('float unclosed.')
                                    continue
                                while new_char.isdigit():
                                    number += new_char
                                    new_char = self.getchar(buffer)
                                self.retract(buffer)
                                tokens += number.ljust(10) + "<" + "float".upper().center(7) + "," + number.center(
                                    7) + ">\n"
                                classes.append('const_float')
                                attris.append(number)
                                line_nums.append(line_num)
                            else:
                                self.retract(buffer)
                                tokens += number.ljust(10) + "<" + "float".upper().center(7) + "," + number.center(
                                    7) + ">\n"
                                classes.append('const_float')
                                attris.append(number)
                                line_nums.append(line_num)
                        elif new_char in {'e', 'E'}:
                            number += new_char
                            new_char = self.getchar(buffer)
                            if new_char in {'+', '-'}:
                                number += new_char
                                new_char = self.getchar(buffer)
                            elif not new_char.isdigit():
                                self.retract(buffer)
                                self.error_handle('float unclosed.')
                                continue
                            while new_char.isdigit():
                                number += new_char
                                new_char = self.getchar(buffer)
                            self.retract(buffer)
                            tokens += number.ljust(10) + "<" + "float".upper().center(7) + "," + number.center(
                                7) + ">\n"
                            classes.append('const_float')
                            attris.append(number)
                            line_nums.append(line_num)
                        else:
                            self.retract(buffer)
                            tokens += number.ljust(10) + "<" + "decimal".upper().center(7) + "," + number.center(
                                    7) + ">\n"
                            classes.append('dec')
                            attris.append(number)
                            line_nums.append(line_num)

            elif new_char == '\"':  # string constant
                line_num = self.row_num
                string = ''
                new_char = self.getchar(buffer)
                while new_char != '\"':
                    string += new_char
                    new_char = self.getchar(buffer)
                    if new_char == 'EOF':
                        self.error_handle("string unclosed.", line_num + 1)
                        break_flag = True
                        break
                tokens += string.ljust(10) + "<" + "STRING".center(7) + "," + string.center(
                        7) + ">\n"
                classes.append('const_string')
                attris.append(string)
                line_nums.append(line_num)
                if break_flag:  # EOF
                    break

            elif new_char == '/':  # may be annotation or division
                line_num = self.row_num
                new_char = self.getchar(buffer)
                if new_char == '*':  #
                    annotation = ''
                    start_row = self.row_num + 1
                    new_char = self.getchar(buffer)
                    while True:
                        annotation += new_char
                        new_char = self.getchar(buffer)
                        if new_char == 'EOF':
                            self.error_handle("annotation unclosed.")
                            break_flag = True
                            break
                        if new_char == '*':
                            new_char = self.getchar(buffer)
                            if new_char == '/':
                                # print("Annotation:from line " + str(start_row)+" to " + str(self.row_num + 1))
                                break  # ignore the annotaion
                            if new_char == 'EOF':
                                self.error_handle("annotation unclosed.")
                                break_flag = True
                                break
                    if break_flag:  # EOF
                        break
                else:  # may be divide operator
                    if new_char == '=':
                        new_char = '/' + new_char
                    else:
                        self.retract(buffer)
                    tokens += new_char.ljust(10) + "<" + new_char.center(7) + "," + '_'.center(
                        7) + ">\n"
                    classes.append(new_char.lower())
                    attris.append('_')
                    line_nums.append(line_num)

            elif new_char in self.OPERATOR:  # operator
                line_num = self.row_num
                new_char += self.getchar(buffer)
                if new_char not in self.OPERATOR:
                    new_char = new_char[:-1]
                    self.retract(buffer)
                tokens += new_char.ljust(10) + "<" + new_char.center(7) + "," + '_'.center(7) + \
                    ">\n"
                classes.append(new_char.lower())
                attris.append('_')
                line_nums.append(line_num)

            elif new_char in self.SEPARATOR:  # separator
                tokens += new_char.ljust(10) + "<" + new_char.center(7) + "," + '_'.center(7) + \
                    ">\n"
                classes.append(new_char.lower())
                attris.append('_')
                line_nums.append(self.row_num)

            else:
                self.error_handle()  # illegal character
            new_char = self.getchar(buffer)
        return tokens[:-1],classes,attris,line_nums

    def client(self, c_file='sem_input.c', output_file='lex_output.txt'):
        """
        scan the c_file and write the token lists to the specific file
        :param c_file: the c programing language source code file,default "sem_input.c"
        :param output_file: path of the file to output the result,default "tokens.txt"
        :return: None
        """
        # read the stream
        with open(c_file, 'r') as read_file:
            buffer = read_file.read().split('\n')  # separate stream in lines
        # scan the c file
        # print("Scanning " + c_file + "......")
        tokens,classes,attris,line_nums = self.scanner(buffer=buffer)
        # write to the output
        # print("Generating " + output_file + '......')
        # with open(output_file, 'w') as output:
        #     output.write(tokens)
        # print("Done.")
        return classes,attris,line_nums


# run the lexer
if __name__ == "__main__":
    Lexer().client(c_file=sys.argv[1], output_file=sys.argv[2] if len(sys.argv) > 2 else 'lex_output.txt')
    # Lexer().client(c_file='sem_input.c', output_file='lex_output.txt')

