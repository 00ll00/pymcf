# PYMCF | py ➡️ mcfunction

**版本：0.1.0-alpha**

python 3.13

minecraft (je) 1.21.8 （其余版本未测试）

## 简介

通过编写 python 代码生成 MC 数据包（以 mcfunction 生成为核心功能），拥有函数调用，流程控制，计分板计算等常规功能，以及内联命令，编译期计算，条件编译等实用功能。

此外，由于 pymcf 开发数据包是完全使用 python 语法开发，可以得到大多数编辑器的高亮和补全支持*，并且可以使用第三方库，或导将你开发的内容导出为代码库供他人调用。

_\* 由于 pymcf 部分语句语义与 python 不同，高亮和类型推断功能可能不准确。_

## 安装

在 GitHub 仓库的 release 页面下载最新的 whl 文件，使用 `pip install xxx.whl` 进行安装。

## 特性列表

- 语言特性
    - 内联命令
    - 判断语句
    - 迭代语句
    - 条件循环语句
    - 异常处理
    - 函数支持*
    - 宏函数支持**
    - 异步函数支持**
    - 引用/导出代码库
    - 编译期计算
    - 编译期条件分支
    - 编译期循环展开
- 标准库
    - 计分板变量及其运算支持
    - nbt 访问支持
    - 目标选择器
    - execute 上下文切换
    - 实体数据结构**
    - 更多数学计算**
- 编译器
    - 函数内联
    - 编译优化*
    - 函数调用栈**
    - 不同 MC 版本的前后端**
    - ast 可视化
    - ir 可视化
    - 生成调试信息*
    - 数据包生成

_\* : 未完全支持或部分功能未实现_

_\*\* : 计划中_

## 语言文档

参考[语言文档](doc/lang.md)。

## 教程

暂时没有，不过可以参考概念验证工程 [psinmc](https://github.com/00ll00/psinmc) 🏃‍♂️。

## 示例

以下是康威生命游戏的实现代码，加载后在主世界 0, 100, 0 处生成画布；使用胡萝卜钓竿时右键可以改变视线指向的细胞的状态，Q 键控制游戏开始或暂停；`/reload`命令可以重置游戏。

```python3
from pathlib import Path

from pymcf.entity import Marker, Player
from pymcf.mc.commands import AtS
from pymcf.project import Project
from pymcf.mcfunction import mcfunction, execute
from pymcf.data import Score, ScoreBoard
from pymcf.text import text_component

project = Project(
  name="gol",
  # prj_install_dir = Path("<数据包导出路径>"),  # 默认导出位置是同目录下 pymcf_out 文件夹
)

# ===============================

BLOCK_EMPTY = "minecraft:black_concrete"
BLOCK_FILLED = "minecraft:white_concrete"

W = 100  # 画布宽
L = 100  # 画板长
assert W * L <= 32768, "画布过大"

MIN_NEB = 2  # 细胞存活最少邻居数
MAX_NEB = 3  # 细胞存活最多邻居数
NEW_NEB = 3  # 细胞繁殖需要的邻居数

MAX_DIST = 100  # 最远光标距离

running = Score("$running", "gol")  # 游戏是否运行


class Cell(Marker):
  """
  细胞实体，继承于 Marker
  """

  @mcfunction
  def try_expand(self):
    """
    在围格子生成新的细胞，若已有细胞或超出画板范围则跳过
    """
    tmp = Score()
    for _dx in range(-1, 2):
      for _dz in range(-1, 2):
        if _dx == 0 and _dz == 0:
          continue
        with execute(f"positioned ~{_dx} ~ ~{_dz} align xyz"):
          tmp = 0
          f'execute store success score {tmp} unless block ~ ~ ~ #minecraft:air unless entity {Cell.select(dx=0, dy=0, dz=0)}'
          if tmp:
            Cell.summon(_tag="new_cell", _pos="~.5 ~.5 ~.5")

  @mcfunction
  def check_neighbors(self):
    """
    检查邻居数量
    """
    num_neighbors = Score(0)
    tmp = Score()
    for _dx in range(-1, 2):
      for _dz in range(-1, 2):
        if _dx == 0 and _dz == 0:
          continue
        f'execute store success score {tmp} positioned ~{_dx} ~ ~{_dz} align xyz if block ~ ~ ~ {BLOCK_FILLED}'
        num_neighbors += tmp
    if num_neighbors < MIN_NEB or num_neighbors > MAX_NEB:
      f'tag @s add dead_cell'
    else:
      f'execute store success score {tmp} if entity @s[tag=new_cell]'
      if tmp and num_neighbors != NEW_NEB:
        f'tag @s add dead_cell'

  @staticmethod
  @mcfunction.manual
  def tick():
    """
    让所有细胞完成一次迭代，此函数可以手动触发
    """
    Cell.select().try_expand()  # 所有细胞先尝试扩展
    Cell.select().check_neighbors()  # 更新所有细胞的状态
    f'execute at @e[tag=dead_cell] run setblock ~ ~ ~ {BLOCK_EMPTY}'
    f'kill @e[tag=dead_cell]'
    f'execute at @e[tag=new_cell] run setblock ~ ~ ~ {BLOCK_FILLED}'
    f'tag @e[tag=new_cell] remove new_cell'


class Operator(Player):
  """
  操作者，继承自玩家
  """

  # Q 键计分板
  key_q = Score(AtS(), ScoreBoard("gol.q", f"minecraft.dropped:minecraft.carrot_on_a_stick"))
  # 右键计分板
  key_rmb = Score(AtS(), ScoreBoard("gol.rmb", f"minecraft.used:minecraft.carrot_on_a_stick"))
  # 是否初始化
  init = Score(AtS(), "gol.init")

  @mcfunction
  def try_init(self):
    """
    初始化初次进入世界的玩家
    """
    # noinspection PyComparisonWithNone
    if self.init == None:  # 判断是否未存在 init 值（不能用 is None）
      self.init = 1
      self.key_q = 0
      self.key_rmb = 0
      f'tp {self} {W / 2} 120 {L / 2}'
      self.give_wand()

  @mcfunction
  def detect_keys(self):
    """
    检测玩家按键
    """
    global running

    if self.key_q:
      self.key_q = 0
      running = not running
      f'kill @e[type=minecraft:item]'
      self.give_wand()
      if running:
        f'tellraw @a "开始迭代"'
      else:
        f'tellraw @a "暂停迭代"'

    if self.key_rmb:
      self.key_rmb = 0
      if running:
        f'tellraw @s {text_component("不能在游戏进行的同时编辑画布！", color="yellow")}'
      else:
        self.change_looking_cell()

  @mcfunction
  def change_looking_cell(self):
    """
    改变玩家视线位置处的细胞状态
    """

    @mcfunction
    def recu(dist: Score):
      """
      递归前进，直到遇到方块或超出最大距离
      """
      if dist <= 0:
        return

      tmp = Score()
      f'execute store success score {tmp} unless block ~ ~ ~ #minecraft:air'
      if tmp:
        f'execute store success score {tmp} align xyz if entity {Cell.select(dx=0, dy=0, dz=0)}'
        if tmp:
          f'execute align xyz run kill {Cell.select(dx=0, dy=0, dz=0)}'
          f'setblock ~ ~ ~ {BLOCK_EMPTY}'
        else:
          with execute("align xyz positioned ~.5 ~.5 ~.5"):
            Cell.summon()
          f'setblock ~ ~ ~ {BLOCK_FILLED}'
        return

      with execute("positioned ^ ^ ^.5"):
        recu(dist - 1)

    with execute("at @s anchored eyes positioned ^ ^ ^"):
      recu(Score(MAX_DIST * 2))

  @mcfunction.inline
  def give_wand(self):
    """
    给玩家魔法棒
    """
    f'item replace entity {self} weapon.mainhand with minecraft:carrot_on_a_stick'


@mcfunction.load
def load():
  """
  全局的初始化函数
  """
  global running
  running = False
  f'kill {Cell.select()}'
  f'forceload add 0 0 {W - 1} {L - 1}'
  f'fill 0 100 0 {W - 1} 100 {L - 1} {BLOCK_EMPTY}'


@mcfunction.tick
def tick():
  """
  全局的 tick 函数
  """
  Operator.select().try_init()
  Operator.select().detect_keys()
  if running:
    Cell.tick()


# ===============================

project.build()
```

## 第三方库

- [nbtlib](https://github.com/vberlier/nbtlib)
- [graphviz](https://github.com/xflr6/graphviz) （可选）
- [dominate](https://github.com/Knio/dominate) （可选）

## 开源许可

- src/pymcf/mc/commands 文件夹由 [Command-Block-Assembly](https://github.com/simon816/Command-Block-Assembly) 项目部分内容整合而来，原项目使用 MIT 协议开源。
