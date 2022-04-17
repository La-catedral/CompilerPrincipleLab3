#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/5/12 下午3:51
# @Author  : Jingshuo Liu
# @File    : Semantic
import sys
from Parser import SyntaxNode
from Lexical import Lexer
from Parser import Parser


class Attribute:  # 文法符号对应的属性类 在分析过程中属性类对象押入栈
    def __init__(self, type='', width=0, name='', val='', addr='', offset='', next=None, true=None, false=None,
                 quad=0,
                 err=False):
        self.type = type  # 变量声明语句中的类型 int float 等
        self.width = width  # 变量声明语句中的类型宽度(字节)
        self.name = name
        self.val = val  # 词法值

        self.addr = addr  # 表达式赋值的综合属性
        self.offset = offset  # 数组表达式赋值语句的综合属性

        self.next = next if next else []  # 控制流语句
        self.true = true if true else []  # bool表达式语句
        self.false = false if false else []
        self.quad = quad  # M->null语句 用于记录下一个语句对应标号

        self.err = err  # 是否遇到了语义错误


class SignTable:
    # 符号表类型
    def __init__(self,outer_idx = 0):
        self.outer_idx = outer_idx
        self.symbol_lst = {}  # {name:(type, offset)}

    def add_symbol(self,name,type,offset):
        self.symbol_lst[name] = (type,offset)  # 标识符以name对应的(类型，偏移量)元祖的形式存在

    def __contains__(self, item):
        return item in self.symbol_lst

    def __len__(self):
        return len(self.symbol_lst)


class Semantic:

    def __init__(self):
        self.offset = 0  # 总偏移量
        self.info = {'t': '', 'w': 0}  # 为产生式右侧变元通过语法树传递信息

        self.tbl_lst = []  # 符号表列表，列表元素为Tbl
        self.tbl_ptr = [0]  # 符号表指针栈[index]index指向self.tbl_lst中的一个符号表
        self.offset_ptr = [0]  # 偏移指针栈 存各个过程的offset

        self.para_q = []  # 过程调用实参的栈，队首在列表最后位置，队尾在index=0处

        self.temp_ptr = -1  # 生成临时变量

        self.code = {}  # 三地址指令和四元式表示{0: (three_addr, quaternion), 1: (three_addr, quaternion)}

        self.attr_stack = []  # 最后位置为栈顶位置
        self.action_dic = {}  # 动作执行
        self.err_info = {}  # 错误信息表
        self.line_num = -1  # 记录行号

    def mk_tbl(self,outer_idx=0):  # 创建一个符号表，并返回其对应的指针（即位置索引）
        self.tbl_lst.append(SignTable(outer_idx))
        return len(self.tbl_lst) - 1

    def enter(self,index:int,name,type,offset:int):  # 想指定的符号表中加入一个新的符号表项
        if not self.tbl_lst:
            self.tbl_lst.append(SignTable(0))
        self.tbl_lst[index].add_symbol(name,type,offset)

    def look_up(self,name,index): # 在用tbl_idx指定的符号表中查找name对应的标识符表项并返回
        while index != -1:
            tbl = self.tbl_lst[index]
            if name in tbl:
                return tbl.symbol_lst[name]
            else:
                index = tbl.outer_idx

    def new_temp(self):
        self.temp_ptr += 1
        return 't%d' % self.temp_ptr  # 按照已经定义的临时变量数量返回变量名t1、t2...

    def get_type_width(self, type: str):
        if type.startswith('array'):
            type = type[type.index('(') + 1:len(type) - 1]
            num, type = type[:type.index(',')], type[type.index(',') + 1:]
            return int(num) * self.get_type_width(type)
        else:
            return 1 if type in ('bool', 'char') else 2 if type == 'short' else 8 if type in ('long', 'double') else 4

    def next_quad(self):
        return len(self.code)

    def back_patch(self, lst:list, quad:int):
        for index in lst:
            self.code[index] = (self.code[index][0] + str(quad),self.code[index][1] + str(quad))

    # 声明语句语义动作
    def rule_12(self):
        # D->proc id ; {N1 D S}
        # {t=top(tblptr); addwidth(t, top(offset));  pop(tblptr);  pop(offset);  enterproc(top(tblptr),id.name,t)}
        t = self.tbl_ptr.pop()  # 弹出当前子过程对应的表以及offset 以便回到父过程
        self.offset_ptr.pop()
        self.enter(self.tbl_ptr[-1], self.attr_stack[-7].val, 'proc', t)  # 向父过程的表中插入一项 借用enter方法 这里的t为表序列指针而非offset
        self.attr_stack = self.attr_stack[:-8] + [Attribute(name='D')]  # 在语义栈保存当前规约出的文法符号

    def rule_62(self):
        # N1->null，t=mktable(top(tblptr)); push(t, tblptr); push(0, offset)
        self.tbl_ptr.append(self.mk_tbl(self.tbl_ptr[-1]))  # 在当前栈顶对应的过程中新建一个子过程的符号表 并将当前符号表指针指向新表
        self.offset_ptr.append(0)  # 新过程的offset更新为0
        self.attr_stack.append(Attribute(name='N1'))  # 语义站加入信息

    def rule_13(self):
        # D->X id C;  X为变量的类型 C用于数组下表的识别
        x_attr, id_val, c_attr = self.attr_stack[-4], self.attr_stack[-3].val, self.attr_stack[-2]
        self.attr_stack = self.attr_stack[:-4] + [Attribute(name='D')]  # 更新语义栈
        if self.look_up(id_val, index=self.tbl_ptr[-1]):  # 在符号表递归中递归查找标识符是否已经存在
            self.err_info[len(self.err_info)] = (self.line_num, '变量重复声明%s' % id_val, '， 忽略本次声明')
        else:
            self.enter(self.tbl_ptr[-1], id_val, c_attr.type, self.offset_ptr[-1])
            self.offset_ptr[-1] += c_attr.width  # 栈顶偏移量变化
            self.offset += c_attr.width  # 程序偏移量变化

    def rule_14(self):
        # D->struct id { N2 D } ;
        id_val = self.attr_stack[-6].val
        self.attr_stack = self.attr_stack[:-7] + [Attribute(name='D')]  # 更新语义栈
        if self.look_up(id_val, self.tbl_ptr[-1]):
            self.err_info[len(self.err_info)] = (self.line_num, '变量重复声明%s' % id_val, '忽略本次记录声明')
        else:
            d_offset = self.offset_ptr.pop()
            self.tbl_ptr.pop()
            self.enter(self.tbl_ptr[-1], id_val, 'record', d_offset)
            self.offset_ptr[-1] += d_offset
            self.offset += d_offset

    def rule_63(self):
        # N2->null {t=mk_tbl(nil); push(t, tbl_ptr), push(0, offset_ptr)}
        self.tbl_ptr.append(self.mk_tbl(-1))  # 为结构体设置的符号表不需要保存指向外层表的指针
        self.offset_ptr.append(0)
        self.attr_stack.append(Attribute(name='N2'))

    def rule_15_22(self):
        # X->long|double|float|int|unsigned|short|bool|char
        val = self.attr_stack.pop().name  # 找到刚压入的非终结符对应的类型 int short 等
        width = 1 if val in ('bool', 'char') else 2 if val == 'short' else 8 if val in ('long', 'double') else 4
        self.info['t'], self.info['w'] = val, width  # 临时变量，用于计算数组类型及宽度
        self.attr_stack.append(Attribute(type=val, width=width))

    def rule_23(self):
        # C->[Num]C {C.type=array(num.val,C1.type); C.width=num.val*C1.width;}
        num, c1 = int(self.attr_stack[-3].val), self.attr_stack[-1]
        self.attr_stack = self.attr_stack[:-4] + [Attribute(type='array(%d,%s)' % (num, c1.type), width=num * c1.width)]

    def rule_24(self):
        # C->null {C.type=t; C.width=w;}
        self.attr_stack.append(Attribute(type=self.info['t'], width=self.info['w']))

    def rule_25_30(self):
        # Num->dec|oct|hex|const_int|const_float|e-notation
        right = self.attr_stack.pop()
        type, name, val = right.type, right.name, right.val
        if name in ['dec', 'oct', 'hex']:
            val = int(val, 10 if name == 'dec' else 16 if name == 'hex' else 8)
        self.attr_stack.append(Attribute(name=name, type=type, val=str(val)))

        """下面是赋值语句翻译语句语句对应的动作"""

    def rule_5(self):
        # S->id=E; {p=lookup(id.lexeme); if p==nil then error; gencode(p'='E.addr); S.nextlist=null}
        id_val, e_addr = self.attr_stack[-4].val, self.attr_stack[-2].addr

        self.attr_stack = self.attr_stack[:-4] + [Attribute(next=[])]  # 对于代表程序语句序列的文法符号S，需要定义next用于程序流控制
        if not self.look_up(id_val, self.tbl_ptr[-1]):
            self.err_info[len(self.err_info)] = (self.line_num, '变量未经声明%s' % id_val, '创建默认声明')
            offset, type = 4, 'int'
            self.enter(self.tbl_ptr[-1], id_val, type, self.offset_ptr[-1])
            self.offset_ptr[-1] += offset
            self.offset += offset

        self.code[len(self.code)] = ('%s = %s' % (id_val, e_addr), '= %s _ %s' % (e_addr, id_val))

    def rule_6(self):
        # S->L=E; {gencode(L.array'['L.offset']''='E.addr); S.nextlist=null}
        l_attr, e_attr = self.attr_stack[-4], self.attr_stack[-2]
        if not l_attr.err:
            three_addr = '%s [ %s ] = %s' % (l_attr.val, l_attr.offset, e_attr.addr)
            quaternion = '[]= %s %s %s' % (e_attr.addr, l_attr.val, l_attr.offset)
            self.code[len(self.code)] = (three_addr, quaternion)
        self.attr_stack = self.attr_stack[:-4] + [Attribute(next=[])]

    def rule_31(self):
        # E->E Op E {E.addr=newtemp(); gencode(E.addr '=' E1.addr 'op' E2.addr);}
        new_temp = self.new_temp()
        e1_attr, op_attr, e2_attr = self.attr_stack[-3], self.attr_stack[-2], self.attr_stack[-1]
        e1_type,e2_type  = self.attr_stack[-3].name,  self.attr_stack[-1].name
        if (e1_type in {'const_string','const_char'} and e2_type in {'dec','oct','hex'})\
                or (e1_type in {'dec','oct','hex'} and e2_type in {'const_string','const_char'}):
            self.err_info[len(self.err_info)] = (self.line_num, '运算分量类型不匹配')
        if ('array' in e1_attr.type and 'array' not in e2_attr.type) or (
                'array' in e2_attr.type and 'array' not in e2_attr.type):
            print(str(self.line_num) +'错误') # todo
        else:
            three_addr = '%s = %s %s %s' % (new_temp, e1_attr.addr, op_attr.name, e2_attr.addr)
            quaternion = '%s %s %s %s' % (op_attr.name, e1_attr.addr, e2_attr.addr, new_temp)
            self.code[len(self.code)] = (three_addr, quaternion)
            self.attr_stack = self.attr_stack[:-3] + [Attribute(addr=new_temp, type=e1_attr.type)]

    def rule_32(self):
        # E->-E {E.addr=newtemp(); gencode(E.addr'=''uminus'E1.addr)}
        e_attr, new_temp = self.attr_stack[-1], self.new_temp()
        self.code[len(self.code)] = ('%s = - %s' % (new_temp, e_attr.addr), '- %s _ %s' % (e_attr.addr, new_temp))
        self.attr_stack = self.attr_stack[:-2] + [Attribute(type=e_attr.type, addr=new_temp)]

    def rule_33(self):
        # E->(E) {E.addr=E1.addr}
        e1_attr = self.attr_stack[-2]
        self.attr_stack = self.attr_stack[:-3] + [Attribute(type=e1_attr.type, addr=e1_attr.addr)]

    def rule_34(self):
        # E->id {E.addr=lookup(id.lexeme); if E.addr==null then error;}
        id_val = self.attr_stack.pop().val
        id_info = self.look_up(id_val, self.tbl_ptr[-1])
        if not id_info:
            self.err_info[len(self.err_info)] = (self.line_num, '变量未经声明%s' % id_val, '创建默认声明')
            offset, type = 4, 'int'
            self.enter(self.tbl_ptr[-1], id_val, type, self.offset_ptr[-1])
            self.offset_ptr[-1] += offset
            self.offset += offset
        self.attr_stack.append(Attribute(type=id_info[0] if id_info else 'int', addr=id_val))

    def rule_35(self):
        # E->L {E.addr=newtemp(); gencode(E.addr'='L.array'['L.offset']');}
        l_attr, new_temp = self.attr_stack.pop(), self.new_temp()
        if not l_attr.err:
            three_addr = '%s = %s [ %s ]' % (new_temp, l_attr.val, str(l_attr.offset))
            quaternion = '=[] %s %s %s' % (l_attr.val, str(l_attr.offset), new_temp)
            self.code[len(self.code)] = (three_addr, quaternion)
            self.attr_stack.append(Attribute(addr=new_temp, type=l_attr.type, val=l_attr.val))
        else:
            self.attr_stack.append(Attribute(addr=new_temp, name='E'))

    def rule_36_38(self):
        # E->Num|const_char|const_string {}
        num = self.attr_stack.pop()
        self.attr_stack.append(Attribute(name=num.name, type=num.type, addr=num.val))

    def rule_39_44(self):
        # Op->+|-|*|/|%|^
        op_val = self.attr_stack.pop().name
        self.attr_stack.append(Attribute(name=op_val))

    def rule_45(self):
        # L->id[E] {L.array=lookup(id.lexeme); if L.array==nil then error; L.type=L.array.type.elem; L.offset=newtemp(); gencode(L.offset'='E.addr'*'L.type.width);}
        id, e_attr = self.attr_stack[-4], self.attr_stack[-2]
        l_symbol = self.look_up(id.val, self.tbl_ptr[-1])
        if l_symbol:
            if 'array' in l_symbol[0]:
                if e_attr.name in ['const_char', 'const_string', 'const_float', 'e-notation']:
                    self.err_info[len(self.err_info)] = (self.line_num, '数组下标不是整数', '忽略该引用')
                    self.attr_stack = self.attr_stack[:-4] + [Attribute(name='L', err=True)]
                else:
                    type = l_symbol[0][l_symbol[0].index(',') + 1:len(l_symbol[0]) - 1]
                    width = self.get_type_width(type)
                    new_t = self.new_temp()
                    self.attr_stack = self.attr_stack[:-4] + [
                        Attribute(offset=new_t, name=id.name, val=id.val, type=type)]
                    three_addr = '%s = %s * %d' % (new_t, e_attr.addr, width)
                    quaternion = '* %s %d %s' % (e_attr.addr, width, new_t)
                    self.code[len(self.code)] = (three_addr, quaternion)
            else:
                self.err_info[len(self.err_info)] = (self.line_num, '对非数组变量使用数组操作符%s' % id.val, '忽略该引用')
                self.attr_stack = self.attr_stack[:-4] + [Attribute(name='L', err=True)]
        else:
            self.err_info[len(self.err_info)] = (self.line_num, '变量未经声明%s' % id.val, '忽略该引用')
            self.attr_stack = self.attr_stack[:-4] + [Attribute(name='L', err=True)]

    def rule_46(self):
        # L->L[E] {L.array=L1.array; L.type=L1.type.elem; t=newtemp(); gencode(t'='E.addr'*'L.type.width); L.offset=newtemp(); gencode(L.offset'='L1.offset'+'t);}
        l_attr, e_attr = self.attr_stack[-4], self.attr_stack[-2]
        new_temp0, new_temp1 = self.new_temp(), self.new_temp()
        if not l_attr.err:
            if 'array' in l_attr.type:
                if e_attr.name in ['const_char', 'const_string', 'const_float', 'e-notation']:
                    self.err_info[len(self.err_info)] = (self.line_num, '数组下标不是整数', '忽略该引用')
                    self.attr_stack = self.attr_stack[:-4] + [Attribute(name='L', err=True)]
                else:
                    type = l_attr.type[l_attr.type.index(',') + 1:len(l_attr.type) - 1]
                    width = self.get_type_width(type)
                    three_addr = '%s = %s * %d' % (new_temp0, e_attr.addr, width)
                    quaternion = '* %s %s %s' % (e_attr.addr, width, new_temp0)
                    self.code[len(self.code)] = (three_addr, quaternion)
                    self.attr_stack = self.attr_stack[:-4] + [
                        Attribute(name=l_attr.name, type=type, offset=new_temp1, val=l_attr.val)]
                    three_addr = '%s = %s + %s' % (new_temp1, l_attr.offset, new_temp0)
                    quaternion = '+ %s %s %s' % (l_attr.offset, new_temp0, new_temp1)
                    self.code[len(self.code)] = (three_addr, quaternion)
            else:
                self.err_info[len(self.err_info)] = (self.line_num, '对非数组变量使用数组操作符%s' % l_attr.val, '忽略该引用')
                self.attr_stack = self.attr_stack[:-4] + [Attribute(name='L', err=True)]
        else:
            self.attr_stack = self.attr_stack[:-4] + [Attribute(name='L', err=True)]

    """布尔表达式语句的回填相关语义动作 =*"""

    def rule_47(self):
        # B->B1 or M B2
        # {backpatch(B1.falselist,M.quad); B.truelist=merge(B1.truelist,B2.truelist); B.falselist=B2.falselist}
        b2_attr = self.attr_stack.pop()  # 依次取出B2 M B1的语义栈中记录的信息
        m_attr = self.attr_stack.pop()
        self.attr_stack.pop()
        b1_attr = self.attr_stack.pop()
        self.attr_stack.append(Attribute(true=b1_attr.true + b2_attr.true, false=b2_attr.false))
        self.back_patch(b1_attr.false, m_attr.quad)

    def rule_65(self):
        # M1->null {M1.quad=nextquad}
        self.attr_stack.append(Attribute(quad=self.next_quad()))  # 返回下一条指令标号

    def rule_48(self):
        # B->B1 and M B2 {backpatch(B1.truelist, M.quad); B.truelist=B2.truelist; B.falselist=merge(B1.falselist, B2.falselist)}
        b2_attr = self.attr_stack.pop()
        m_attr = self.attr_stack.pop()
        self.attr_stack.pop()
        b1_attr = self.attr_stack.pop()
        self.attr_stack.append(Attribute(true=b2_attr.true, false=b1_attr.false + b2_attr.false))
        self.back_patch(b1_attr.true, m_attr.quad)

    def rule_49(self):
        #  B->not B1 {B.truelist=B1.falselist; B.falselist=B1.truelist}
        b1_attr = self.attr_stack.pop()
        self.attr_stack.pop()
        self.attr_stack.append(Attribute(true=b1_attr.false, false=b1_attr.true))

    def rule_50(self):
        # B->(B1) {B.truelist=B1.truelist;B.falselist=B1.falselist}
        self.attr_stack.pop()
        b1_attr = self.attr_stack.pop()
        self.attr_stack.pop()
        self.attr_stack.append(Attribute(true=b1_attr.true, false=b1_attr.false))

    def rule_51(self):
        # B->E Relop E {B.truelist=makelist(nextquad); B.falselist= makelist(nextquad+1) gencode('if' E1.addr relop.op E2.addr 'goto –'); gencode('goto –')}
        e2_addr = self.attr_stack.pop().addr
        relop_val = self.attr_stack.pop().name
        e1_addr = self.attr_stack.pop().addr
        self.attr_stack.append(Attribute(true=[self.next_quad()], false=[self.next_quad() + 1]))
        three_addr = 'if %s %s %s goto ' % (e1_addr, relop_val, e2_addr)
        quaternion = 'j%s %s %s ' % (relop_val, e1_addr, e2_addr)
        self.code[len(self.code)] = (three_addr, quaternion)
        self.code[len(self.code)] = ('goto ', 'j _ _ ')

    def rule_52_53(self):
        # B->true {B.truelist=makelist(nextquad); gencode('goto –')}
        # B->false {B.falselist=makelist(nextquad); gencode('goto –')}
        attr_val, make_lst = self.attr_stack.pop().name, [self.next_quad()]
        b_attr = Attribute(true=make_lst) if attr_val == 'true' else Attribute(false=make_lst)
        self.attr_stack.append(b_attr)
        self.code[len(self.code)] = ('goto ', 'j _ _ ')

    def rule_54_59(self):
        # Relop-><|<=|==|!=|>|>=
        attr = self.attr_stack.pop()
        self.attr_stack.append(Attribute(name=attr.name))

    """控制流语句的语义动作回填相关"""

    def rule_4(self):
        #  S->S1 M S2 {backpatch(S1.nextlist, M.quad); S.nextlist=S2.nextlist}
        s1_attr, m_attr, s2_attr = self.attr_stack[-3], self.attr_stack[-2], self.attr_stack[-1]
        self.attr_stack = self.attr_stack[:-3] + [Attribute(next=s2_attr.next)]
        self.back_patch(s1_attr.next, m_attr.quad)

    def rule_7(self):
        # S->if B then M S1 {backpatch(B.truelist, M.quad); S.nextlist=merge(B.falselist, S1.nextlist)}
        s1_attr, m_attr, b_attr = self.attr_stack[-1], self.attr_stack[-2], self.attr_stack[-4]
        self.attr_stack = self.attr_stack[:-5] + [Attribute(next=b_attr.false + s1_attr.next)]
        self.back_patch(b_attr.true, m_attr.quad)

    def rule_8(self):
        # S->if B then M1 S1 N3 else M2 S2
        # {backpatch(B.truelist, M1.quad); backpatch(B.falselist, M2.quad);
        # S.nextlist=merge(S1.nextlist, merge(N3.nextlist, S2.nextlist))}
        s2_attr, m2_attr, n_attr, s1_attr, m1_attr, b_attr = self.attr_stack[-1], self.attr_stack[-2], self.attr_stack[
            -4], self.attr_stack[-5], self.attr_stack[-6], self.attr_stack[-8]
        self.attr_stack = self.attr_stack[:-9] + [Attribute(next=s1_attr.next + s2_attr.next + n_attr.next)]
        self.back_patch(b_attr.true, m1_attr.quad)
        self.back_patch(b_attr.false, m2_attr.quad)

    def rule_64(self):
        # N3->null {N3.nextlist=makelist(nextquad); gencode('goto –')}
        self.attr_stack.append(Attribute(next=[self.next_quad()]))
        self.code[len(self.code)] = ('goto ', 'j _ _ ')

    def rule_9(self):
        # S->while M1 B do { M2 S1 }
        # {backpatch(S1.nextlist, M1.quad); backpatch(B.truelist,M2.quad);
        # S.nextlist=B.falselist; gencode('goto'M1.quad)}
        s_attr, m2_attr, b_attr, m1_attr = self.attr_stack[-2], self.attr_stack[-3], self.attr_stack[-6], \
                                           self.attr_stack[-7]
        self.attr_stack = self.attr_stack[:-8] + [Attribute(next=b_attr.false)]
        self.back_patch(s_attr.next, m1_attr.quad)
        self.back_patch(b_attr.true, m2_attr.quad)
        self.code[len(self.code)] = ('goto %d' % m1_attr.quad, 'j _ _ %d' % m1_attr.quad)

    """过程调用语句的语义动作相关"""

    def rule_10(self):
        # S->call id ( Elst ) ;
        # {n=0; for queue中的每个t do {gencode('param't); n=n+1} gencode('call'id.addr','n);} {S.nextlist=null;}
        elst_attr, id_val = self.attr_stack[-3], self.attr_stack[-5].val
        self.attr_stack = self.attr_stack[:-6] + [Attribute(next=[])]
        res = self.look_up(id_val, self.tbl_ptr[-1])
        if res:
            if res[0] != 'proc':
                self.err_info[len(self.err_info)] = (self.line_num, '对非过程名使用过程调用操作符%s' % id_val, '忽略该调用')
            else:
                for para in reversed(self.para_q):
                    self.code[len(self.code)] = ('param %s' % para, 'param _ _ %s' % para)
                self.code[len(self.code)] = (
                    'call %s , %d' % (id_val, len(self.para_q)), 'call %s %d _' % (id_val, len(self.para_q)))
        else:
            self.err_info[len(self.err_info)] = (self.line_num, '函数未经声明%s' % id_val, '忽略该调用')

    def rule_60(self):
        # Elst->Elst,E {将E.addr添加到q的队尾}
        e_attr = self.attr_stack[-1]
        self.attr_stack = self.attr_stack[:-3] + [Attribute()]
        self.para_q.insert(0, e_attr.addr)

    def rule_61(self):
        # Elst->E {将q初始化为只包含E.addr}
        e_attr = self.attr_stack.pop()
        self.para_q = [e_attr.addr]
        self.attr_stack.append(Attribute())

    def rule_0(self):
        # P'->P
        self.attr_stack.pop()
        self.attr_stack.append(Attribute(name='P'))

    def rule_1(self):
        # P->DP
        self.attr_stack = self.attr_stack[:-2] + [Attribute(name='P')]

    def rule_2(self):
        # P->S M1 P
        s_attr, m_attr = self.attr_stack[-3], self.attr_stack[-2]
        self.back_patch(s_attr.next, m_attr.quad)
        self.attr_stack = self.attr_stack[:-3] + [Attribute(name='P')]

    def rule_3(self):
        # P->null
        self.attr_stack.append(Attribute(name='P'))

    def rule_11(self):
        # D->DD
        self.attr_stack = self.attr_stack[:-2] + [Attribute(name='D')]

    def semantic_run(self, tokens, nums_attr, syntax):  # 运行语义分析
        def set_children():  # 由于自底向上分析只能获得父节点，因此需要再次处理，设置子节点
            for node in all_nodes:
                if node.parent is not None:
                    node.parent.add_child(node)

        for func in dir(self):  # 初始化action_dic语义动作表
            if func.startswith('rule_'):
                item, func = func.split('_'), 'self.%s()' % func
                if len(item) == 2:
                    self.action_dic[int(item[1])] = func  # item[1]号产生式对应的语义动作押入栈中 以便调用
                else:
                    idx, idy = int(item[1]), int(item[2])
                    for count in range(idx, idy + 1):
                        self.action_dic[count] = func

        self.mk_tbl(-1)  # 创建主过程对应符号表 因为外层不再有符号表 该符号表的外指符号表索引设置为-1

        sep, syntax_lst, states, tokens, nodes, all_nodes, syntax_err = ' ', [], [0], tokens + ['$'], ['$'], [], []
        nums_attr.append('$')

        while True:
            top_token, top_state, top_num_attr = tokens[0], states[0], nums_attr[0]
            if top_token not in syntax.table[top_state]:
                flag = True
                for idx, state in enumerate(states):  # 从符号栈自栈顶向下扫描，找到第一个可以跳转的符号以及对应的非终结符A的GOTO目标
                    for non_term in syntax.non_terminals:
                        if non_term in syntax.table[state]:
                            top_state = syntax.table[state][non_term]
                            for idy, token in enumerate(tokens):  # 忽略输入token，直到找到一个合法的可以跟在A后的token
                                if token in syntax.table[top_state]:
                                    symbols = [nodes[count].symbol for count in range(idx)]
                                    symbols.reverse()
                                    symbols.extend(tokens[:idy])
                                    syntax_err.append(
                                        (top_num_attr[0], top_token + ' : ' + str(top_state), '移入' + sep.join(
                                            tokens[:idy]) + '  规约' + non_term + ' -> ' + sep.join(symbols)))
                                    # 移入操作
                                    for item, num_attr in zip(tokens[:idy], nums_attr[:idy]):
                                        syntax_node = SyntaxNode(item, line_num=num_attr[0], attribute=num_attr[1])
                                        all_nodes.append(syntax_node)
                                        nodes.insert(0, syntax_node)
                                    syntax_lst.append((sep.join(list(map(str, states))), sep.join(tokens),
                                                       '错误恢复：移入' + sep.join(tokens[:idy])))
                                    # 规约操作
                                    parent_node = SyntaxNode(non_term)
                                    for syntax_node in nodes[:len(symbols)]:
                                        syntax_node.set_parent(parent_node)
                                    all_nodes.append(parent_node)
                                    syntax_lst.append((sep.join(list(map(str, states))), sep.join(tokens),
                                                       '错误恢复：规约：' + non_term + ' -> ' + sep.join(symbols)))

                                    # 删除栈顶符号，保留state, 并将goto(s, A)压入栈；忽略输入符号，保留token
                                    states, nodes = [top_state] + states[idx:], [parent_node] + nodes[len(symbols):]
                                    nums_attr, tokens, flag = nums_attr[idy:], tokens[idy:], False
                                    break
                        if not flag:  # 找到则跳出循环
                            break
                    if not flag:  # 找到则跳出循环
                        break
            else:
                op = syntax.table[top_state][top_token].split()
                if op[0] == 'acc':
                    syntax_lst.append((sep.join(list(map(str, states))), sep.join(tokens), '成功：' + syntax.start_symbol))
                    all_nodes.append(syntax.tree)
                    nodes[0].set_parent(syntax.tree)
                    set_children()
                    return syntax_lst, syntax_err
                elif op[0] == 's':  # 移入
                    syntax_lst.append((sep.join(list(map(str, states))), sep.join(tokens), '移入：' + top_token))
                    states.insert(0, int(op[1]))
                    syntax_node = SyntaxNode(top_token, line_num=top_num_attr[0], attribute=top_num_attr[1])
                    all_nodes.append(syntax_node)
                    nodes.insert(0, syntax_node)
                    tokens.pop(0)
                    nums_attr.pop(0)
                    self.line_num = top_num_attr[0]
                    self.attr_stack.append(Attribute(name=top_token, val=top_num_attr[1]))  # 终结符会被押入语义栈 方便调用语义动作
                elif op[0] == 'r':  # 规约
                    non_term, symbols = syntax.rules[int(op[1])]
                    syntax_lst.append((sep.join(list(map(str, states))), sep.join(tokens),
                                       '规约：' + non_term + ' -> ' + sep.join(symbols)))
                    if symbols[0] == syntax.empty_str:  # 空产生式，特殊处理
                        null_node = SyntaxNode(syntax.empty_str)
                        all_nodes.append(null_node)
                        nodes.insert(0, null_node)
                    parent_node = SyntaxNode(non_term)
                    all_nodes.append(parent_node)
                    for syntax_node in nodes[:len(symbols)]:
                        syntax_node.set_parent(parent_node)
                    nodes = nodes[len(symbols):]
                    nodes.insert(0, parent_node)
                    states = states[len(symbols) if symbols[0] != syntax.empty_str else 0:]
                    states.insert(0, syntax.table[states[0]][non_term])
                    eval(self.action_dic[int(op[1])])  # 执行op[1]号产生式对应的语义动作



    def client(self,input_path,output_path):
        classes, attris, line_nums = Lexer().client(c_file=input_path, output_file='output/lex_output.txt')
        linenum_and_attributes = []
        for i in range(len(attris)):
            linenum_and_attributes.append((line_nums[i] + 1, attris[i]))
        parser = Parser('input/grammar.txt')
        self.semantic_run(tokens=classes,nums_attr=linenum_and_attributes,syntax=parser)

        out_flow = ''
        for index in self.code:
            code = self.code[index]  # 取出该条代码
            buf = "(" + str(code[1]).replace(' ',',') + ")"
            out_flow += str(index).ljust(3) + ": " + buf.ljust(24) + str(code[0]).ljust(
                10) + "\n"
        with open(output_path,'w') as output_file:
            output_file.write(out_flow[:-1])

        print("\ntables:")
        for tbl in self.tbl_lst:
            print(tbl.symbol_lst)
            print()

        # print(self.err_info)
        for key in self.err_info:
            strin = 'Semantic error at Line [' + str(self.err_info[key][0]) + ']: [' + self.err_info[key][1] + '].'
            print(strin)
        return


if __name__ == '__main__':
    Semantic().client(input_path='input/sem_input.c', output_path='output/semantic_out.txt')
    # Semantic().client(input_path='input/wrong_1.c', output_path='output/semantic_out.txt')
    # Semantic().client(input_path='input/wrong_2.c', output_path='output/semantic_out.txt')
    # Semantic().client(input_path='input/wrong_3.c', output_path='output/semantic_out.txt')
    # Semantic().client(input_path='input/wrong_4.c', output_path='output/semantic_out.txt')


