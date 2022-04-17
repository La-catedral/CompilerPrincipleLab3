#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/5/1 下午3:07
# @Author  : Jingshuo Liu
# @File    : Parser

import sys
import copy
import Lexical


class Parser:

    def __init__(self, grammar_file_path):
        self.start_symbol = ''  # 文法开始符号
        self.empty_str = 'null'  # 默认null为文法中的空串表示
        self.terminals = []  # 终结符号集合
        self.non_terminals = []  # 非终结符集合
        self.rules = []  # 所有的文法规则
        self.first = {}  # 所有文法符号的First集合
        self.item_collection = []  # 文法的所有项目:[(idx, idy, a)]，其中idx指的是文法规则编号，idy指的是原点所在的位置,a为展望符
        self.table = {}  # LR(1)预测分析表
        self.tree = None  # 语法分析树
        self.output_flow = ''
        self.init_parser(grammar_file_path)
        return

    def init_parser(self, grammar_file_path):
        self.load_data(grammar_file_path)
        self.get_sig_first()
        self.get_collection()
        self.get_analysis_table()
        self.tree = SyntaxNode(self.start_symbol)
        return

    def load_data(self, grammar_file_path):
        with open(grammar_file_path, 'r', encoding='utf-8') as input_file:
            grammar_list = input_file.readlines()
            for line in grammar_list:  # 初始化非终结符以及产生式列表
                if line.strip() != '':  # 跳过空行
                    split_product = line.split('->')  # 将产生式按照左右空行切分
                    symbol = split_product[0].strip()  # 产生式左部符号
                    right_list = split_product[1].split()  # 产生式右部符号列表
                    if self.start_symbol == '':
                        self.start_symbol = symbol  # 以第一个扫描到的产生式左部符号作为开始符号
                    if symbol not in self.non_terminals:
                        self.non_terminals.append(symbol)
                    new_rule = (symbol, right_list)
                    if new_rule not in self.rules:
                        self.rules.append(new_rule)
            for production in self.rules:  # 初始化终结符
                right_list = production[1]
                for sign in right_list:
                    if sign not in self.non_terminals and sign not in self.terminals:
                        self.terminals.append(sign)
            self.terminals.remove('null')
            self.terminals.append('$')
            print(self.rules)

        return

    def get_sig_first(self):
        # 生成所有文法符号的FIRST集
        self.first = {terminal: [terminal] for terminal in self.terminals}
        for non_terminal in self.non_terminals:
            self.first[non_terminal] = []  # 对变元的first集合首先初始化为空
        repeat_flag = True
        while repeat_flag:
            repeat_flag = False
            for non_terminal, right_list in self.rules:
                # break_flag = False
                if right_list == [self.empty_str]:
                    if self.empty_str not in self.first[non_terminal]:
                        self.first[non_terminal].append(self.empty_str)
                        repeat_flag = True
                    continue
                for signal in right_list:
                    for new_first in self.first[signal]:
                        if new_first != self.empty_str and new_first not in self.first[non_terminal]:
                            self.first[non_terminal].append(new_first)
                            repeat_flag = True
                    if self.empty_str in self.first[signal]:  # 如果当前这个在产生式右部的符号能推导出空串 则继续查看下一个符号
                        continue
                    else:
                        break
                if self.empty_str in self.first[right_list[-1]] and self.empty_str not in self.first[
                    non_terminal]:
                    self.first[non_terminal].append(self.empty_str)
                    repeat_flag = True
        return

    def get_str_first(self, sign_list):
        str_first = []
        if sign_list:  # 如果符号串不为空
            for sign in sign_list:
                break_flag = False
                str_first.extend(sig for sig in self.first[sign] if sig not in str_first and sig != self.empty_str)
                if self.empty_str not in self.first[sign]:
                    break
            if  self.empty_str in self.first[sign_list[-1]] and self.empty_str not in str_first:
                    str_first.append(self.empty_str)
        return str_first

    def get_closure(self, item_list):
        # 计算项目集的闭包 输入一个包含若干个项目(i,j,sign)的集合，生成其闭包
        closure = item_list.copy()
        for item in closure:
            non_terminal, right_list = self.rules[item[0]]  # 从rules中第item[0]号产生式
            if item[1] < len(right_list) and right_list[item[1]] not in self.terminals:
                new_non_terminal = right_list[item[1]]
                for rule_index, rule in enumerate(self.rules):
                    if rule[0] == new_non_terminal:
                        str_first = self.get_str_first(right_list[item[1] + 1:] + [item[2]])
                        for first in str_first:
                            new_item = (rule_index, 0, first)
                            if new_item not in closure:
                                closure.append(new_item)
        return closure

    def goto(self, product_set, next_symbol):
        goto_set = []
        for product in product_set:
            non_terminal, right_list = self.rules[product[0]]  # 找到项目给出的product[0]号产生式
            if product[1] != len(right_list) and next_symbol == right_list[product[1]]:
                goto_set.append((product[0], product[1] + 1, product[2]))
        return self.get_closure(goto_set)

    def get_collection(self):
        self.item_collection.append(self.get_closure([(0, 0, '$')]))
        for index, product_set in enumerate(self.item_collection):
            self.table[index] = {}
            for symbol in self.non_terminals + self.terminals:
                goto_set = self.goto(product_set, symbol)
                if goto_set:
                    if goto_set not in self.item_collection:
                        next_index = len(self.item_collection)
                        self.item_collection.append(goto_set)
                    else:
                        next_index = self.item_collection.index(goto_set)
                    self.table[index][symbol] = next_index
        return

    def get_analysis_table(self):
        former_table = copy.deepcopy(self.table)
        for index, product_set in enumerate(self.item_collection):  # 对于DFA的每一个状态
            for product in product_set:
                non_terminal, right_list = self.rules[product[0]]  # 去rules中寻找第prodiuct[0]号产生式
                # info = ''
                if product[1] == len(right_list) and non_terminal == self.start_symbol and product[2] == '$':
                    self.table[index][product[2]] = 'acc'
                elif right_list[0] == self.empty_str:
                    self.table[index][product[2]] = 'r ' + str(product[0])
                elif product[1] == len(right_list) and non_terminal != self.start_symbol:
                    self.table[index][product[2]] = 'r ' + str(product[0])
                elif right_list[product[1]] in self.terminals:
                    self.table[index][right_list[product[1]]] = 's ' + str(former_table[index][right_list[product[1]]])

        return

    def sparse(self, tokens, linenum_and_attributes):
        """
        main function for class Syntax,sparse the input and get the syntax tree
        :return:
        """

        def set_child_for_nodes():
            for node in all_nodes:
                if node.parent is not None:
                    node.parent.add_child(node)
                    node.parent.set_line_num()

        tokens = tokens + ['$']  # tokens看作输入缓冲区，并在末尾加入结尾标识符$
        linenum_and_attributes.append('$')

        state_stack = [0]  # 状态栈
        nodes = ['$']  # 存储文法符号对应节点的栈 用于构建语法树
        all_nodes = []  # 存储已经生成的节点

        syntax_lst = []  # 用于保存语法处理信息
        syntax_error = []  # 存储错误信息
        separator = ' '  # 便于生成提示信息的分隔符

        while True:
            current_token, current_line_attr, current_state = tokens[0], linenum_and_attributes[0], state_stack[0]
            if current_token not in self.table[int(current_state)]:  # 如果读到的下一个符号在分析表中被标记为错误的跳转
                # 读到非法符号 进行错误处理
                flag = True
                for index, state in enumerate(state_stack):  # 从栈顶开始找目标状态S
                    for non_term in self.non_terminals:  # 寻找目标变元A
                        if non_term in self.table[int(state)]:
                            new_state = self.table[int(state)][non_term]  # 找到能够goto的下一个状态
                            for token_index, token in enumerate(tokens):
                                if token in self.table[int(new_state)]:
                                    former_symbols = [nodes[count].symbol for count in
                                                      range(index)]  # 找到栈中截止到S的节点序列对应的符号序列
                                    former_symbols.reverse()
                                    former_symbols.extend(tokens[:token_index])  # 加上输入缓冲区的几个字符
                                    strin = 'Syntax error at Line [' + str(nodes[index].line_num) + ']: [Syntax error].'
                                    if strin not in syntax_error:
                                        syntax_error.append(strin)

                                    # 进行移入
                                    for item, num_attr in zip(tokens[:token_index],
                                                              linenum_and_attributes[:token_index]):
                                        new_syntax_node = SyntaxNode(item, line_num=num_attr[0], attribute=num_attr[1])
                                        all_nodes.append(new_syntax_node)
                                        nodes.insert(0, new_syntax_node)
                                    syntax_lst.append(
                                        ('状态栈： ' + separator.join(list(map(str, state_stack))), "输入缓冲区： " +
                                         separator.join(tokens), '错误恢复：移进 ' + current_token))
                                    # 进行规约
                                    parent_node = SyntaxNode(non_term,line_num=nodes[len(former_symbols)-1].line_num)
                                    for syntax_node in nodes[:len(former_symbols)]:
                                        syntax_node.set_parent(parent_node)
                                    all_nodes.append(parent_node,)
                                    syntax_lst.append(
                                        ('状态栈： ' + separator.join(list(map(str, state_stack))), "输入缓冲区： " +
                                         separator.join(tokens),
                                         '错误恢复：规约： ' + non_terminal + ' -> ' + separator.join(right_list)))
                                    state_stack,nodes = [new_state] + state_stack[index:],[parent_node] + nodes[len(former_symbols):]
                                    linenum_and_attributes,tokens,flag = linenum_and_attributes[token_index:],tokens[token_index:],False
                                    break
                        if not flag:  # 找到状态s及对应的变元A则跳出循环
                            break
                    if not flag:  # 找到状态s及对应的变元A则跳出循环
                        break
            else:
                action = self.table[int(current_state)][current_token].split()
                if action[0] == 's':
                    syntax_lst.append(('状态栈： ' + separator.join(list(map(str, state_stack))), "输入缓冲区： " +
                                       separator.join(tokens), '移进： ' + current_token))
                    state_stack.insert(0, action[1])  # 将下一个状态押入状态栈
                    this_node = SyntaxNode(symbol=current_token, line_num=current_line_attr[0],
                                           attribute=current_line_attr[1])
                    all_nodes.append(this_node)  # 为构建作准备
                    nodes.insert(0, this_node)
                    tokens.pop(0)  # 将输入指针向后移动一位
                    linenum_and_attributes.pop(0)
                elif action[0] == 'r':
                    non_terminal, right_list = self.rules[int(action[1])]  # 寻找用于规约的产生式子
                    syntax_lst.append(('状态栈： ' + separator.join(list(map(str, state_stack))), "输入缓冲区： " +
                                       separator.join(tokens),
                                       '规约： ' + non_terminal + ' -> ' + separator.join(right_list)))
                    if right_list[0] == self.empty_str:
                        null_node = SyntaxNode(self.empty_str)  # 空串不作为输入文件中的词素，不再分配行号，最后在输出文件中也不打印
                        all_nodes.append(null_node)
                        nodes.insert(0, null_node)
                    parent_node = SyntaxNode(non_terminal,line_num=nodes[len(right_list)-1].line_num)
                    all_nodes.append(parent_node)
                    for syntax_node in nodes[:len(right_list)]:
                        syntax_node.set_parent(parent_node)
                    nodes = nodes[len(right_list):]
                    nodes.insert(0, parent_node)
                    state_stack = state_stack[len(right_list) if right_list[0] != self.empty_str else 0:]
                    state_stack.insert(0, self.table[int(state_stack[0])][non_terminal])  # goto 并押入下一状态
                elif action[0] == 'acc':
                    # 到达接收状态 继续填充构建信息 并且设置树根
                    syntax_lst.append(('状态栈： ' + separator.join(list(map(str, state_stack))), "输入缓冲区： " +
                                       separator.join(tokens), '成功： ' + self.start_symbol))
                    all_nodes.append(self.tree)
                    nodes[0].set_parent(self.tree)
                    set_child_for_nodes()
                    return syntax_lst, syntax_error  # 返回语法树构建信息 以及语法错误信息

    def client(self, file_to_sparse='input/sem_input.c',output_file='output/out.txt'):
        classes,attris,line_nums = Lexical.Lexer().client(c_file=file_to_sparse, output_file='lex_output.txt')
        linenum_and_attributes = []
        for i in range(len(attris)):
            linenum_and_attributes.append((line_nums[i]+1,attris[i]))

        syntax_lst , syntax_err = self.sparse(classes,linenum_and_attributes)
        for err in syntax_err:
            print(err)

        def write_to(node, n):
            for i in range(n):
                self.output_flow += ' '
            self.output_flow += node.__str__() + '\n'
            for child_node in node.children:
                write_to(child_node, n + 2)
        write_to(self.tree,0)

        with open(output_file,'w') as output:
            output.write(self.output_flow[:-1])

        with open('output/table.txt','w') as table_out:
            for key in self.table:
                table_out.write(str(key) + " : " + str(self.table[key]) + '\n')

        with open('output/syntax_list.txt','w') as info_out:
            flow = ''
            for info in syntax_lst:
                flow += str(info) + '\n'
                info_out.write(flow[:-1])
        return


class SyntaxNode:
    def __init__(self, symbol, children=None, line_num=0, attribute=''):
        self.symbol = symbol  # 当前节点的文法符号 比如IDN
        self.children = [] if children is None else children  # 当前文法符号产生式的右部
        self.parent = None  # 当前符号的父节点
        self.line_num = line_num  # 该token在c源文件中的行号
        self.attribute = attribute  # 词法属性值 比如某一IDN的attr是a 而某个keyword是_

    def add_child(self, child):
        self.children.append(child)

    def set_parent(self, parent):
        self.parent = parent

    def set_line_num(self):  # 将父节点行号设置为最左孩子的行号
        if self.children:
            self.line_num = self.children[0].line_num

    def __str__(self):
        info = self.symbol
        if self.attribute and self.attribute != '_':
            info += ' :' + self.attribute
        if self.line_num:  # 因为空串不作为词素，所以对应的节点不输出行号
            info += ' (' + str(self.line_num) + ')'
        return info


if __name__ == '__main__':
    Parser('input/my_grammar.txt').client(file_to_sparse=sys.argv[1], output_file=sys.argv[2] if len(sys.argv) > 2 else 'output/out.txt')
    # Parser('input/my_grammar.txt').client(file_to_sparse='input/sem_input.c',output_file='output/out.txt')
