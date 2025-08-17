# pymcf 语言：

pymcf 使用 100% 的原生 python 语法，但对部分语义进行调整以扩展语言功能。

## 函数

- **函数定义**

通过`@mcfunction`装饰器及其变种可以将一个 python 函数标记为 mcfunction。**所有语义扩展只发生在`@mcfunction`标记的函数中**。关于函数定义的更多细节见 [mcfunction](./mcfunction.md)。

```python3
from pymcf.project import Project
from pymcf.mcfunction import mcfunction

project = Project("testpack")  # 初始化工程，设置工程名称为 testpack（也是编译后数据包命名空间）


@mcfunction.load  # 数据包加载时自动调用
def test():
    f'say hello world!'  # 插入内联命令


project.build()  # 构建数据包
```

以上定义了一个简单的函数，`mcfunction.load`是`mcfunction`的一个变种，表示此函数编译后拥有`#minecraft:load`
的标签，会在数据包加载时自动调用一次。

此函数内容只有一个 `say hello world!` 命令。

使用 python 运行这个脚本后会在当前文件夹下产生一个`pymcf_out`的文件夹，编译完成的数据包 "testpack.zip" 位于其中。将其放在
minecraft 存档的数据包文件夹内，在数据包加载时可以看到 "hello world!" 打印在游戏聊天栏中。

你可以指定构建的数据包的安装位置，更多配置见 [Project](./project.md)。

- **函数调用**

mcfunction 函数的调用和普通 python 函数相同。（由于现阶段未实现调用栈，当函数需要被循环调用时需要额外注意中间变量的干扰）

```python3
from pymcf.project import Project
from pymcf.mcfunction import mcfunction
from pymcf.text import text_component

project = Project("testpack")


@mcfunction.manual  # 手动调用
def test():
    broadcast("准备……")
    for i in range(5, 0, -1):
        broadcast(i)
    broadcast("游戏开始!!!")


@mcfunction.inline  # 内联函数，其函数内容被搬移到调用处
def broadcast(content):
    f'tellraw @a ["广播：",{text_component(content, color="yellow")}]'


project.build()
```

以上数据包加载后，通过在游戏中调用以下函数触发：

```mcfunction
function testpack:test
```

## 内联命令

当一个 **格式化字符串（f-str）** 的值未被使用时，被视为一个内联命令。内联命令在求值后会被就地插入 mcfunction 中。

```python3
from pymcf.project import Project
from pymcf.mcfunction import mcfunction

project = Project("testpack")


@mcfunction.manual
def test():
    f'say 这个命令会被插入生成的文件中！'

    f"""say 引号的形式不影响编译"""

    (f'say '
     f'这种写法被 python 视为单个字符串，'
     f'也是可以的'
     )

    text = "这种写法"
    f'say 在格式化字符串中，当然可以使用{text}'

    f'say 但是这个不行，' + f'因为字符串参与了加法运算'

    print(f'也就是说你可以正常使用 f-str 编写代码，比如这条文本会在编译时被打印在控制台，而不会干扰数据包生成')

project.build()
```

## 赋值

当一个 python 赋值语句左边的表达式（左值）已经是一个运行期变量时，再次对其赋值会生成赋值语句。

pymcf 的赋值看着很乱，也的确如此。编译期量和运行期量在赋值语句上的表现不同，因此建议通过特殊的命名方式区分编译期变量与运行期变量。

```python3
from pymcf.project import Project
from pymcf.mcfunction import mcfunction
from pymcf.data import Score

project = Project("testpack")


@mcfunction.manual
def test():
    a = Score()  # 生成一个临时计分板变量，存放于 a
    a = 1  # 将这个计分板变量赋值为 1
    print(f"此时 a 的类型是 {type(a)}")  # 此 print 为 编译期 python 原生的 print，可以看到 a 仍是一个 Score 对象
    f'tellraw @a ["a=",{a:json}]'  # 在游戏中输出 a 的值 1

    _b = 10  # _b 是编译期变量 10
    a = _b   # 将 b 的值赋值到 a，此时 a 仍是 Score
    f'tellraw @a ["现在，a=",{a:json}]'  # 在游戏中输出 a 的值 10  

    a = None  # 计分板变量赋值 None 表示 reset 这个计分板量
    print(f"现在 a 的类型是 {type(a)}")  # 可以看到此时 a 仍然是 Score 对象
    
    if False:  # 为了不进一步降低代码可读性，请不要这样做……
      
      c = a   # 看起来没问题，但实际上 a 和 c 都是同一个计分板对象
      c += 1  # 此时 a 的值也被改变了
      
      d = Score(a)  # 这样写可以从 a 复制出一个新的变量，此后 d 和 a 互不干扰
      
      _b = a  # 向一个编译期变量赋予运行期变量，编译期量会被顶替。此时 _b 也和 a 是同一个对象了
        
        
project.build()
```

## if 语句

- **运行期**

当一个 if 语句判断条件是运行期值，则会生成一个运行期条件语句。

- if 语句的判断条件类型为 Bool，若不是则会隐性将其转化为 Bool。
- 语句可以包含多个 `elif` 分支和一个 `else` 分支。
- 不应当在运行期期 if 语句中修改编译期变量，这是违背逻辑的，使用了会出现意料之外的结果（目前无法检测这种行为，不会有警告，需要自行注意）

```python3
from pymcf.project import Project
from pymcf.mcfunction import mcfunction
from pymcf.data import Score

project = Project("testpack")


@mcfunction.manual
def test():
    y = Score()
    f'execute store result score {y} run data get entity @s Pos[1]'  # 获取你的 y 值

    if y >= 100:  # y >= 100 是一个运行期的条件
        # y >= 100 时进入这个分支
        f'say 你站的太高了'
        f'tp @s ~ 50 ~'
        print("if 分支被编译了！")
    else:
        # y < 100 时进入这个分支
        f'say 你站的不够高'
        f'tp @s ~ 150 ~'
        print("else 分支被编译了！")


project.build()
```

可以看到编译完成时控制台有两个分支被编译的信息，这是因为运行期的条件语句在编译时所有分支的内容会依次被编译。

- **编译期**

if 语句判断的量是编译期量时，完全按照 python 的运行逻辑完成代码生成。

```python3
from pymcf.project import Project
from pymcf.mcfunction import mcfunction
from pymcf.data import Score

project = Project("testpack")

DEBUG = True  # 控制是否编译调试内容，试试改成 False


@mcfunction.manual
def test():
    y = Score()
    f'execute store result score {y} run data get entity @s Pos[1]'  # 获取你的 y 值

    if DEBUG:  # 判断编译方式
        # 如果以调试模式编译
        f'tellraw @a ["debug info: y=",{y:json},", 200-y=",{200 - y:json}]'
        print("现在是调试模式，if 分支被编译了！")
    else:
        # 如果不以调试模式编译
        f'tellraw @a ["你现在距离山顶还差",{200 - y:json},"米"]'
        print("现在不是调试模式，else 分支被编译了！")


project.build()
```

由于 `DEBUG` 是一个编译期的量，因此此处的 if 语句控制的是编译期的流程，只有一个分支被运行。

## for 语句

- **运行期**

当 for 语句的迭代器是一个运行期迭代器时，会生成运行期的迭代逻辑。

- for 语句从一个运行期迭代器中不断取值，直到迭代器抛出 `RtStopIteration` 异常。
- 语句中可以使用 `continue` 和 `break`，其行为与 python 相同。
- 可以存在 else 分支，只有当迭代器正常完成迭代时才进入此分支。

```python3
from pymcf.project import Project
from pymcf.mcfunction import mcfunction
from pymcf.data import Score, Range

project = Project("testpack")

var = Score("var", "test")  # 定义变量 var，绑定到游戏中 var 的 test 计分板值


@mcfunction.load
def load():
    global var
    var = 10


@mcfunction.manual
def test():
    sum = Score(0)  # 定义计分板临时变量 sum，并初始化为 0
    for i in Range(var):  # Range 是运行期可迭代对象，用法类似 range
        sum += i
        f'tellraw @s ["加上",{i:json},"，总共为",{sum:json}]'
        if sum > 100:
            f"say var 够大了！"
            break  # 跳出 for 循环
    else:  # 未被 break 时触发
        f'say var 不够大。'


project.build()
```

你可以在游戏中改变 var 的值，观察函数的不同行为：

```mcfunction
/scoreboard players set var test 20
```

- **编译期**

for 语句迭代对象是编译期量时，会按照 python 的运行逻辑完成代码生成。

```python3
from pymcf.project import Project
from pymcf.mcfunction import mcfunction

project = Project("testpack")

_var = 10


@mcfunction.manual
def test():
    for _i in range(_var):  # 编译期迭代展开，等效于在此处写了 10 个 say 命令
        f'say {"你好" * _i}！'


project.build()
```

## while 语句

类比 `for` 语句。

## try 语句

`try` 用于捕获运行期异常，不能用于捕获编译期异常。其流程控制逻辑与 python `try` 语句相同。

- try 语句必须拥有至少一个 `except` 分支或者一个 `finally` 分支。
- try 语句可以包含多个 `except` 分支，一个 `finally` 分支，一个 `else` 分支。
- try 只能捕获运行期异常。

## raise 语句

`raise` 用于抛出异常。可以抛出运行期异常或编译期异常。

当抛出编译期异常时视为编译存在错误，会终止编译。

## with 语句

`with` 语句和 python `with` 相同，功能完全由提供的上下文管理对象决定。

## match 语句

_TODO_