from functools import partial
import csv
import urllib.request
import json
from urllib.parse import urljoin
from itertools import combinations_with_replacement

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QLabel, QCheckBox, QHBoxLayout,
    QMessageBox, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt
import sys
import pandas as pd
import os


# 定义用于存储刻印数据的文件路径
FOLDER_PATH = "data"
DATA_FILE = os.path.join(FOLDER_PATH, "mintmark_data.csv")
JSON_FILE = os.path.join(FOLDER_PATH, "mintmark_data.json")
COMBINATIONS_FILE = os.path.join(FOLDER_PATH, "combinations_data.csv")
ONLY1_MINTMARK_CLASS_FILE = os.path.join(FOLDER_PATH, "only1_mintmark_class.txt")
ONLY1_MINTMARK_IDS_FILE = os.path.join(FOLDER_PATH, "only1_mintmark_ids.txt")

MISSING_MINTMARK_IDS_FILE = os.path.join(FOLDER_PATH, "missing_mintmark_ids.txt") # 用户没有这个刻印
PROCESS_FILE = os.path.join(FOLDER_PATH, "process.csv")

excel_file = "结果.xlsx"

# 创建数据文件夹
os.makedirs(FOLDER_PATH, exist_ok=True)

# 限1刻印的系列id，例如65是"精灵王誓约"
content = [
    "57", "61", "65", "66", "67", "74", "75", "78", "80", "83", "84", "85"
]

# 将内容写入txt文件，每个数字占一行
def write_content_to_file(file_path, content):
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write("\n".join(content) + "\n")
        print(f"文件 '{file_path}' 创建成功并写入内容。")
    else:
        print(f"文件 '{file_path}' 已存在，未修改。")

write_content_to_file(ONLY1_MINTMARK_CLASS_FILE, content)

# 读取 `only1_mintmark_class.txt` 中的系列 id
def load_only1_mintmark_class():
    try:
        with open(ONLY1_MINTMARK_CLASS_FILE, 'r', encoding='utf-8-sig') as f:
            only1_mintmark_class = set(line.strip() for line in f if line.strip())
        return only1_mintmark_class
    except FileNotFoundError:
        return set()

# 加载限1刻印的系列 id
only1_mintmark_class = load_only1_mintmark_class()

# 加载用户没有的刻印 id
def load_missing_mintmark_ids():
    try:
        with open(MISSING_MINTMARK_IDS_FILE, 'r', encoding='utf-8-sig') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()  # 如果文件不存在，返回一个空集合


# 下载并保存 JSON 数据的方法
def download_and_store_json():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        version_url = "http://seerh5.61.com/version/version.json"
        req = urllib.request.Request(version_url, headers=headers)
        response = urllib.request.urlopen(req, timeout=10)
        version_data = json.load(response)

        files = version_data.get("files", {})
        resource = files.get("resource", {})
        config = resource.get("config", {})
        xml = config.get("xml", {})

        mintmark_url = urljoin("http://seerh5.61.com/resource/config/xml/", xml.get("mintmark.json", ""))

        req = urllib.request.Request(mintmark_url, headers=headers)
        response = urllib.request.urlopen(req, timeout=10)
        mintmark_data = json.load(response)

        with open(JSON_FILE, 'w', encoding='utf-8-sig') as f:
            json.dump(mintmark_data, f, ensure_ascii=False, indent=4)
        print(f"MintMark JSON 数据已保存到文件 {JSON_FILE}")
    except urllib.error.URLError as e:
        print(f"网络错误：{e}")
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误：{e}")
    except Exception as e:
        print(f"发生未知错误: {e}")

# 更新 JSON 数据为 CSV 文件的方法
# 更新 JSON 数据为 CSV 文件的方法
def convert_json_to_csv():
    try:
        # 加载用户缺失的刻印 ID
        missing_mintmark_ids = load_missing_mintmark_ids()  # 加载缺失的刻印 ID

        # 打开 JSON 文件读取数据
        with open(JSON_FILE, 'r', encoding='utf-8-sig') as f:
            mintmark_data = json.load(f)

        MintMarks = mintmark_data.get("MintMarks", {})
        MintMark = MintMarks.get("MintMark", [])

        # 写入到 CSV 文件
        with open(DATA_FILE, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ["id", "quality", "description", "total_attr_value", "total_sum", "monster_id",
                          "mintmark_class"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for mintmark in MintMark:
                try:
                    if mintmark.get("Type", 0) != 3:
                        continue

                    # 获取刻印的 ID
                    id = mintmark.get("ID", 0)
                    id_str = str(id)
                    # 如果该刻印在缺失 ID 列表中，跳过
                    if id_str in missing_mintmark_ids:
                        continue
                    quality = mintmark.get("Quality", 0)
                    description = mintmark.get("Des", "")
                    monster_id = mintmark.get("MonsterID", "")
                    mintmark_class = mintmark.get("MintmarkClass", "")

                    max_attr_value = mintmark.get("MaxAttriValue", "")
                    extra_attr_value = mintmark.get("ExtraAttriValue", "")
                    max_values = [int(num) for num in max_attr_value.split()]
                    extra_values = [int(num) for num in extra_attr_value.split()] if extra_attr_value else [0] * len(
                        max_values)
                    total_values = [max_val + extra_val for max_val, extra_val in zip(max_values, extra_values)]
                    total_attr_value = " ".join(map(str, total_values))
                    total_sum = sum(total_values)

                    writer.writerow({
                        "id": id,
                        "quality": quality,
                        "description": description,
                        "total_attr_value": total_attr_value,
                        "total_sum": total_sum,
                        "monster_id": monster_id,
                        "mintmark_class": mintmark_class
                    })
                except (KeyError, ValueError):
                    continue

        print(f"MintMark 数据已保存到文件 {DATA_FILE}")
    except Exception as e:
        print(f"转换 JSON 数据到 CSV 时发生错误: {e}")

def ensure_data_prepared():
    """
    确保 JSON 数据已经下载并且成功转换为 CSV。
    """
    # 检查 JSON 文件是否存在，如果不存在则下载数据
    if not os.path.exists(JSON_FILE):
        print("JSON 文件不存在，正在下载 JSON 数据...")
        download_and_store_json()

    # 检查 CSV 文件是否存在，如果 JSON 已存在但 CSV 未生成，则生成 CSV
    if os.path.exists(JSON_FILE) and not os.path.exists(DATA_FILE):
        print("CSV 文件不存在，从 JSON 生成 CSV 文件...")
        convert_json_to_csv()



# 加载限1刻印的 id
def load_only1_mintmark_ids():
    # 确保数据已经被下载和准备
    ensure_data_prepared()

    try:
        with open(ONLY1_MINTMARK_IDS_FILE, 'r', encoding='utf-8-sig') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []


# 读取 csv 文件并生成限1刻印的 id 文件
def generate_only1_mintmark_ids():
    # 确保数据已经被下载和准备
    ensure_data_prepared()

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            filtered_rows = []

            # 过滤 mintmark_class 在限1刻印系列中的行
            for row in reader:
                if row['mintmark_class'] in load_only1_mintmark_class():
                    filtered_rows.append(row['id'])

            # 写入到新的 txt 文件，每行一个 id
            if filtered_rows:
                if not os.path.exists(ONLY1_MINTMARK_IDS_FILE):
                    with open(ONLY1_MINTMARK_IDS_FILE, 'w', newline='', encoding='utf-8-sig') as txtfile:
                        for row_id in filtered_rows:
                            txtfile.write(row_id + "\n")
                    print(f"文件 '{ONLY1_MINTMARK_IDS_FILE}' 创建成功并写入限1刻印的 id 数据。")
                else:
                    print(f"文件 '{ONLY1_MINTMARK_IDS_FILE}' 已存在，未修改。")
            else:
                print("没有匹配到任何限1刻印的数据。")
    else:
        print(f"文件 '{DATA_FILE}' 不存在，请检查路径。")

# 创建缺失的刻印 ID 文件
def create_missing_mintmark_ids_file():
    if not os.path.exists(MISSING_MINTMARK_IDS_FILE):
        with open(MISSING_MINTMARK_IDS_FILE, 'w', encoding='utf-8') as file:
            file.write("# 请输入您没有（或者不想用）的刻印 ID，每个 ID 占一行。并且在输入之后点击“更新刻印文件”按钮。\n")
        print(f"文件 '{MISSING_MINTMARK_IDS_FILE}' 已创建。")
    else:
        print(f"文件 '{MISSING_MINTMARK_IDS_FILE}' 已存在，未修改。")




# 实现添加总和列的功能
# 在此阶段排除来自同一系列的三个刻印组合，并且确保only1系列的刻印最多只有一个
def find_initial_combinations(filtered_mintmark_list, attribute_targets, symmetric=False, use_only1=False):
    ids, descriptions, mintmark_classes, attr_values_list = [], [], [], []

    only1_ids = []
    # 加载限制的系列id
    if use_only1:
        only1_ids = load_only1_mintmark_ids()  # 加载`only1`系列的ID集，用于后续判断
        only1_ids = set(int(x) for x in only1_ids)  # 将 only1_ids 中的所有元素转换为整数


    # 遍历 filtered_mintmark_list 提取每个刻印的属性
    for mintmark in filtered_mintmark_list:
        try:
            total_attr_values = [int(num) for num in mintmark["total_attr_value"].split()]
            if len(total_attr_values) != 6:
                continue
        except ValueError:
            continue

        attr_values_list.append(total_attr_values)
        ids.append(int(mintmark["id"]))  # 将ID存储为整数类型，便于后续排序
        descriptions.append(mintmark["description"])
        mintmark_classes.append(mintmark["mintmark_class"])

    candidates = list(range(len(ids)))
    initial_combinations = []  # 使用列表来存储组合，便于后续排序
    data_to_save = []

    for combination in combinations_with_replacement(candidates, 3):
        class_counts = {mintmark_classes[i]: combination.count(i) for i in combination}

        # 确保最多只有两个刻印来自于同一系列
        if any(count > 2 for count in class_counts.values()):
            continue

        # 确保没有三个刻印来自于同一系列
        if len(set([mintmark_classes[i] for i in combination])) == 1:
            continue

        # 如果需要对称性，确保组合中恰好有两个相同的元素
        if symmetric:
            if len(set(combination)) > 2:
                continue
            if not any(count == 2 for count in class_counts.values()):
                continue

        # 检查组合中的刻印ID是否有重复
        ids_in_combination = [ids[i] for i in combination]
        unique_ids = set(ids_in_combination)

        if len(unique_ids) < len(ids_in_combination):
            # 如果有重复ID，检查是否属于限1系列
            for i in combination:
                if ids_in_combination.count(ids[i]) > 1:
                    if ids[i] in only1_ids:
                        # 如果限1系列的刻印有重复ID，跳过这个组合
                        valid_combination = False
                        break
            else:
                valid_combination = True

            if not valid_combination:
                continue

        # **对组合的刻印ID从大到小排序**
        sorted_combination = sorted(combination, key=lambda i: ids[i], reverse=True)

        # 添加到初步组合列表
        initial_combinations.append(tuple(sorted_combination))

    # 对所有组合进行排序，优先比较第一个刻印的ID，如果相同则比较第二个，以此类推
    initial_combinations = sorted(initial_combinations, key=lambda comb: tuple(ids[i] for i in comb), reverse=True)

    # 检查属性目标是否符合要求，并准备数据保存到文件
    for combination in initial_combinations:
        valid_combination = all(
            target_min <= sum(attr_values_list[i][attr_index] for i in combination) <= target_max
            for attr_index, (target_min, target_max) in attribute_targets.items()
        )
        if valid_combination:
            attr_values_sum = [
                sum(attr_values_list[i][attr_index] for i in combination) for attr_index in range(6)
            ]
            total_sum = sum(attr_values_sum[attr_index] for attr_index in attribute_targets if
                            attribute_targets[attr_index] != (0, 0))
            data_to_save.append([descriptions[i] for i in combination] + attr_values_sum + [total_sum])

    # 将初步组合保存到文件，增加"总和"列
    columns = ["刻印1", "刻印2", "刻印3", "攻击", "防御", "特攻", "特防", "速度", "体力", "选项总和"]
    df = pd.DataFrame(data_to_save, columns=columns)
    df.to_csv(COMBINATIONS_FILE, index=False, encoding='utf-8-sig')

    return initial_combinations


# 初步过滤刻印数据的方法
def initial_filtering(mintmark_list, monster_id_filter=None, quality_filter=None, filter_low_values=False,
                      total_sum_filter=None, attribute_targets=None, improve_efficiency=False, top_n=200):
    filtered_mintmark_list = []
    used_monster_ids = set()  # 用于记录已经使用过的专属刻印

    for row in mintmark_list:
        # 获取当前刻印的 monster_id
        monster_id = row.get("monster_id")

        # 如果这个刻印是专属刻印
        if monster_id:
            # 如果用户没有输入monster_id，跳过
            if monster_id_filter is None:
                continue
            # 如果刻印的 monster_id 与用户输入不匹配，跳过
            if monster_id != monster_id_filter:
                continue
            # 如果该 monster_id 已经被使用过，跳过
            if monster_id in used_monster_ids:
                continue
            # 记录使用过的专属刻印
            used_monster_ids.add(monster_id)



        if row['quality'] == '5' and total_sum_filter:
            try:
                total_sum = int(row['total_sum'])
                if not any([
                    ('>220' in total_sum_filter and total_sum > 220),
                    ('=220' in total_sum_filter and total_sum == 220),
                    ('<220' in total_sum_filter and total_sum < 220)
                ]):
                    continue
            except ValueError:
                continue

        # 质量过滤
        if quality_filter and row["quality"] not in quality_filter:
            continue

        # 过滤低属性值的刻印
        if filter_low_values:
            try:
                total_attr_values = [int(num) for num in row["total_attr_value"].split()]
                if any(value < 0 for value in total_attr_values):
                    continue
            except ValueError:
                continue

        # 将符合条件的刻印加入列表
        filtered_mintmark_list.append(row)

    # 如果用户在两个或更多属性上设定了下限，且勾选了提高效率选项，则先进行排序并只保留前 top_n 个
    if improve_efficiency and attribute_targets:
        relevant_indices = [index for index, (min_value, max_value) in attribute_targets.items() if min_value > 0]
        if len(relevant_indices) >= 2:
            filtered_mintmark_list.sort(
                key=lambda x: sum(int(x["total_attr_value"].split()[i]) for i in relevant_indices),
                reverse=True
            )
            filtered_mintmark_list = filtered_mintmark_list[:top_n]

    return filtered_mintmark_list


# 进一步过滤刻印，基于“特定属性必须为 0”
def filter_zero_requirements(mintmark_list, attribute_targets):
    filtered_list = []
    for mintmark in mintmark_list:
        try:
            total_attr_values = [int(num) for num in mintmark["total_attr_value"].split()]
            if len(total_attr_values) != 6:
                continue
        except ValueError:
            continue

        valid = True
        for attr_index, target_range in attribute_targets.items():
            target_min, target_max = target_range
            if target_min == 0 and target_max == 0 and total_attr_values[attr_index] != 0:
                valid = False
                break

        if valid:
            filtered_list.append(mintmark)
    return filtered_list

# 验证刻印组合是否符合所有条件（从文件中读取）
def validate_combinations(attribute_targets, attributes):
    valid_combinations = []

    # 尝试读取 combinations_file，如果文件不存在则返回空列表
    try:
        df = pd.read_csv(COMBINATIONS_FILE, encoding='utf-8-sig')
    except FileNotFoundError:
        return valid_combinations

    # 打开 process 文件以追加数据
    with open(PROCESS_FILE, mode='a', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)

        # 检查文件是否为空，如果为空则写入头部
        file.seek(0, 2)  # 移动到文件末尾
        if file.tell() == 0:  # 如果文件为空，则写入头部
            writer.writerow(["刻印1", "刻印2", "刻印3", "攻击", "防御", "特攻", "特防", "速度", "体力", "选项总和"])

        for _, row in df.iterrows():
            valid = True

            # 确保最多只有两个刻印来自于同一个系列
            class_counts = {}
            for col in ["刻印1", "刻印2", "刻印3"]:
                mintmark_class = row[col]
                if mintmark_class not in class_counts:
                    class_counts[mintmark_class] = 0
                class_counts[mintmark_class] += 1

            if any(count > 2 for count in class_counts.values()):
                continue

            for attr_index, (target_min, target_max) in attribute_targets.items():
                total_value = row[attributes[attr_index]]
                if not (target_min <= total_value <= target_max):
                    valid = False
                    break

            if valid:
                combination_data = [row[col] for col in ["刻印1", "刻印2", "刻印3", "攻击", "防御", "特攻", "特防", "速度", "体力", "选项总和"]]
                valid_combinations.append(combination_data)
                # 将有效的组合数据写入 result.csv 文件
                writer.writerow(combination_data)

    # 读取 CSV 文件，确保使用正确的编码
    df = pd.read_csv(COMBINATIONS_FILE, encoding='utf-8-sig')



    # 将 DataFrame 保存为 Excel 文件
    df.to_excel(excel_file, index=False, engine='openpyxl')
    return valid_combinations

#
# # 生成组合并写入 CSV 文件
# def generate_combinations_and_write_to_file(content, combinations_file):
#     if not os.path.exists(combinations_file):
#         combinations = list(combinations_with_replacement(content, 2))
#         with open(combinations_file, 'w', encoding='utf-8', newline='') as csvfile:
#             writer = csv.writer(csvfile)
#             writer.writerow(["combination_1", "combination_2"])
#             writer.writerows(combinations)
#         print(f"文件 '{combinations_file}' 创建成功并写入组合数据。")
#     else:
#         print(f"文件 '{combinations_file}' 已存在，未修改。")
#
# # 生成并保存组合
# generate_combinations_and_write_to_file(content, COMBINATIONS_FILE)
#
#
# # 处理并写入 JSON 文件
# def process_and_write_json(data_file, json_file):
#     if os.path.exists(data_file):
#         df = pd.read_csv(data_file, encoding='utf-8-sig')
#         df_filtered = df[df['mintmark_class'].isin(only1_mintmark_class)]
#         df_filtered.to_json(json_file, orient='records', force_ascii=False)
#         print(f"文件 '{json_file}' 创建成功并写入过滤后的数据。")
#     else:
#         print(f"文件 '{data_file}' 不存在，请检查路径。")
#
# # 处理并保存 JSON 文件
# process_and_write_json(DATA_FILE, JSON_FILE)

# 创建 GUI
def create_gui():
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle('刻印筛选工具 ——By 摩尔曼斯克')
    window.resize(1080, 800)
    layout = QVBoxLayout()

    form_layout = QFormLayout()
    input_fields = {}
    attributes = ['攻击', '防御', '特攻', '特防', '速度', '体力']

    for index, attr in enumerate(attributes):
        row_layout = QHBoxLayout()
        min_field = QLineEdit()
        max_field = QLineEdit()
        row_layout.addWidget(QLabel(f'{attr}范围:'))
        row_layout.addWidget(min_field)
        row_layout.addWidget(QLabel(' - '))
        row_layout.addWidget(max_field)

        reset_button = QPushButton('置0')
        clear_button = QPushButton('清空')

        # 使用 make_reset_function 生成每个 reset 按钮的绑定函数
        def make_reset_function(min_field, max_field):
            return lambda: (min_field.setText("0"), max_field.setText("0"))

        reset_button.clicked.connect(make_reset_function(min_field, max_field))

        # 使用 partial 传递不同的 min_field 和 max_field 实例
        clear_button.clicked.connect(partial(lambda min_f, max_f: (min_f.clear(), max_f.clear()), min_field, max_field))

        row_layout.addWidget(reset_button)
        row_layout.addWidget(clear_button)

        form_layout.addRow(row_layout)
        input_fields[index] = (min_field, max_field)

    monster_id_field = QLineEdit()
    form_layout.addRow('专属精灵ID:', monster_id_field)

    symmetric_checkbox = QCheckBox("对称")
    form_layout.addRow(symmetric_checkbox)

    only1_checkbox = QCheckBox("限1刻印验证")
    only1_checkbox.setChecked(True)
    form_layout.addRow(only1_checkbox)

    improve_efficiency_layout = QHBoxLayout()
    improve_efficiency_checkbox = QCheckBox("提升效率【可能会缺失刻印】")
    improve_efficiency_checkbox.setChecked(True)
    improve_efficiency_layout.addWidget(improve_efficiency_checkbox)

    top_n_field = QLineEdit()
    top_n_field.setText("200")
    top_n_field.setFixedWidth(50)
    improve_efficiency_layout.addWidget(QLabel("只选择5项总和位次前"))
    improve_efficiency_layout.addWidget(top_n_field)
    improve_efficiency_layout.addWidget(QLabel("的刻印"))

    spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
    improve_efficiency_layout.addItem(spacer)
    form_layout.addRow(improve_efficiency_layout)

    filter_low_values_checkbox = QCheckBox("去除属性值过低的刻印（低于目标值的五分之一）")
    filter_low_values_checkbox.setChecked(True)
    form_layout.addRow(filter_low_values_checkbox)

    quality_checkboxes = {}
    qualities = {'5角': '5', '4角': '4', '3角': '3', '2角': '2'}
    quality_row_layout = QHBoxLayout()
    for label, value in qualities.items():
        checkbox = QCheckBox(label)
        if label == '5角':
            checkbox.setChecked(True)
        quality_row_layout.addWidget(checkbox)
        quality_checkboxes[value] = checkbox
    form_layout.addRow(QLabel('选择刻印类别:'), quality_row_layout)

    total_sum_checkboxes = {}
    total_sum_conditions = {'大于220': '>220', '等于220': '=220', '小于220': '<220'}
    total_sum_row_layout = QHBoxLayout()
    for label, value in total_sum_conditions.items():
        checkbox = QCheckBox(label)
        if label == '大于220':
            checkbox.setChecked(True)
        total_sum_row_layout.addWidget(checkbox)
        total_sum_checkboxes[value] = checkbox
    form_layout.addRow(QLabel('5项总和条件（仅对5角刻印）:'), total_sum_row_layout)

    filter_button = QPushButton('筛选刻印组合')
    download_button = QPushButton('下载刻印数据')
    update_button = QPushButton('更新刻印文件')
    result_table = QTableWidget()
    result_table.setColumnCount(10)
    result_table.setHorizontalHeaderLabels(
        ["刻印1", "刻印2", "刻印3", "攻击", "防御", "特攻", "特防", "速度", "体力", "选项总和"]
    )

    def on_filter_button_clicked():
        attribute_targets = {}
        for index, (min_field, max_field) in input_fields.items():
            min_value = min_field.text().strip()
            max_value = max_field.text().strip()
            try:
                if min_value and not max_value:
                    attribute_targets[index] = (int(min_value), float('inf'))
                elif max_value and not min_value:
                    attribute_targets[index] = (float('-inf'), int(max_value))
                elif min_value and max_value:
                    min_value, max_value = int(min_value), int(max_value)
                    if min_value > max_value:
                        QMessageBox.warning(window, "输入错误", f"{attributes[index]} 的最小值不能大于最大值。")
                        return
                    attribute_targets[index] = (min_value, max_value)
            except ValueError:
                QMessageBox.warning(window, "输入错误", f"{attributes[index]} 的值无效，请输入整数。")
                return

        monster_id = monster_id_field.text().strip()
        symmetric = symmetric_checkbox.isChecked()
        use_only1 = only1_checkbox.isChecked()
        improve_efficiency = improve_efficiency_checkbox.isChecked()
        filter_low_values = filter_low_values_checkbox.isChecked()
        quality_filter = [value for value, checkbox in quality_checkboxes.items() if checkbox.isChecked()]
        total_sum_filter = [value for value, checkbox in total_sum_checkboxes.items() if checkbox.isChecked()]
        try:
            top_n = int(top_n_field.text().strip())
        except ValueError:
            QMessageBox.warning(window, "输入错误", "请在提升效率选项中输入有效的整数值。")
            return

        try:
            mintmark_list = []
            with open(DATA_FILE, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    mintmark_list.append(row)
        except FileNotFoundError:
            QMessageBox.critical(window, "错误", f"文件 {DATA_FILE} 未找到，请先下载数据。")
            return

        # 调用初步过滤和验证的方法，这些可以根据需要进一步完善
        filtered_mintmark_list = initial_filtering(mintmark_list, monster_id_filter=monster_id,
                                                   quality_filter=quality_filter, filter_low_values=filter_low_values,
                                                   total_sum_filter=total_sum_filter, attribute_targets=attribute_targets,
                                                   improve_efficiency=improve_efficiency, top_n=top_n)
        filtered_mintmark_list = filter_zero_requirements(filtered_mintmark_list, attribute_targets)
        find_initial_combinations(filtered_mintmark_list, attribute_targets, symmetric=symmetric, use_only1=use_only1)
        valid_combinations = validate_combinations(attribute_targets, attributes)

        if valid_combinations:
            result_table.setRowCount(len(valid_combinations))
            for row_idx, combination in enumerate(valid_combinations):
                for col_idx, value in enumerate(combination):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignCenter)  # 设置文本居中
                    result_table.setItem(row_idx, col_idx, item)
        else:
            result_table.setRowCount(0)
            QMessageBox.information(window, "结果", "未找到符合条件的刻印组合。")

    filter_button.clicked.connect(on_filter_button_clicked)
    download_button.clicked.connect(download_and_store_json)
    update_button.clicked.connect(convert_json_to_csv)

    layout.addLayout(form_layout)
    layout.addWidget(filter_button)
    layout.addWidget(download_button)
    layout.addWidget(update_button)
    layout.addWidget(result_table)

    window.setLayout(layout)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    ensure_data_prepared()  # 确保 JSON 和 CSV 数据已准备好
    create_missing_mintmark_ids_file()  # 创建缺失刻印 ID 文件
    generate_only1_mintmark_ids()  # 生成限1刻印的 ID 文件
    create_gui()  # 启动 GUI 应用程序
