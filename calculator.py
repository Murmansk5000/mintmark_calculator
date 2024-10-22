import csv
import urllib.request
import json
from urllib.parse import urljoin
from itertools import combinations_with_replacement

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QFormLayout,
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QLabel, QCheckBox, QHBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt
import sys
import pandas as pd

# 定义用于存储刻印数据的 CSV 文件路径
data_file = "data/mintmark_data.csv"
json_file = "data/mintmark_data.json"
combinations_file = "data/combinations_data.csv"

# 下载并保存 JSON 数据的方法
def download_and_store_json():
    try:
        # 添加请求头
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

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(mintmark_data, f, ensure_ascii=False, indent=4)
        QMessageBox.information(None, "成功", f"MintMark JSON 数据已保存到文件 {json_file}")
    except urllib.error.URLError as e:
        QMessageBox.critical(None, "网络错误", f"网络错误：{e}")
    except json.JSONDecodeError as e:
        QMessageBox.critical(None, "JSON 解析错误", f"JSON 解析错误：{e}")
    except Exception as e:
        QMessageBox.critical(None, "未知错误", f"发生未知错误: {e}")

# 更新 JSON 数据为 CSV 文件的方法
def convert_json_to_csv():
    try:
        # 从 JSON 文件中加载数据
        with open(json_file, 'r', encoding='utf-8') as f:
            mintmark_data = json.load(f)

        # 提取 MintMarks 数据
        MintMarks = mintmark_data.get("MintMarks", {})
        MintMark = MintMarks.get("MintMark", [])

        # 将数据保存到 CSV 文件（只保留 Type 为 3 的刻印，并去掉 Type 列，只保存总和列）
        with open(data_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["id", "quality", "description", "total_attr_value", "total_sum", "monster_id", "mintmark_class"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for mintmark in MintMark:
                try:
                    if mintmark.get("Type", 0) != 3:
                        continue
                    id = mintmark.get("ID", 0)
                    quality = mintmark.get("Quality", 0)
                    description = mintmark.get("Des", "")
                    monster_id = mintmark.get("MonsterID", "")
                    mintmark_class = mintmark.get("MintmarkClass", "")

                    # 计算 MaxAttriValue 和 ExtraAttriValue 的加和
                    max_attr_value = mintmark.get("MaxAttriValue", "")
                    extra_attr_value = mintmark.get("ExtraAttriValue", "")
                    max_values = [int(num) for num in max_attr_value.split()]
                    extra_values = [int(num) for num in extra_attr_value.split()] if extra_attr_value else [0] * len(max_values)
                    total_values = [max_val + extra_val for max_val, extra_val in zip(max_values, extra_values)]
                    total_attr_value = " ".join(map(str, total_values))

                    # 计算 total_attr_value 列中所有数值的总和
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
        QMessageBox.information(None, "成功", f"MintMark 数据已保存到文件 {data_file}")
    except Exception as e:
        QMessageBox.critical(None, "错误", f"转换 JSON 数据到 CSV 时发生错误: {e}")

# 初步过滤刻印数据的方法
def initial_filtering(mintmark_list, monster_id_filter=None, quality_filter=None, filter_low_values=False, total_sum_filter=None):
    filtered_mintmark_list = []
    for row in mintmark_list:
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

        if monster_id_filter:
            if row.get("monster_id") != monster_id_filter:
                continue
        else:
            if row.get("monster_id"):
                continue

        if quality_filter and row["quality"] not in quality_filter:
            continue

        if filter_low_values:
            try:
                total_attr_values = [int(num) for num in row["total_attr_value"].split()]
                if any(value < 0 for value in total_attr_values):
                    continue
            except ValueError:
                continue

        filtered_mintmark_list.append(row)
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

# 实现添加总和列的功能
# 在此阶段排除来自同一系列的三个刻印组合
def find_initial_combinations(filtered_mintmark_list, attribute_targets, symmetric=False):
    ids, descriptions, mintmark_classes, attr_values_list = [], [], [], []

    for mintmark in filtered_mintmark_list:
        try:
            total_attr_values = [int(num) for num in mintmark["total_attr_value"].split()]
            if len(total_attr_values) != 6:
                continue
        except ValueError:
            continue

        attr_values_list.append(total_attr_values)
        ids.append(mintmark["id"])
        descriptions.append(mintmark["description"])
        mintmark_classes.append(mintmark["mintmark_class"])

    candidates = list(range(len(ids)))
    initial_combinations = set()  # 使用集合来确保唯一性
    data_to_save = []

    for combination in combinations_with_replacement(candidates, 3):
        class_counts = {mintmark_classes[i]: combination.count(i) for i in combination}
        # 确保最多只有两个刻印来自于同一个系列
        if any(count > 2 for count in class_counts.values()):
            continue

        # 确保没有三个刻印来自于同一个系列
        if len(set([mintmark_classes[i] for i in combination])) == 1:
            continue

        if symmetric:
            # Ensure that there are exactly two identical elements in the combination
            if len(set(combination)) > 2:
                continue
            if not any(count == 2 for count in class_counts.values()):
                continue

        valid_combination = all(
            target_min <= sum(attr_values_list[i][attr_index] for i in combination) <= target_max
            for attr_index, (target_min, target_max) in attribute_targets.items()
        )
        if valid_combination:
            initial_combinations.add(combination)
            attr_values_sum = [
                sum(attr_values_list[i][attr_index] for i in combination) for attr_index in range(6)
            ]
            total_sum = sum(attr_values_sum[attr_index] for attr_index in attribute_targets if attribute_targets[attr_index] != (0, 0))
            data_to_save.append([descriptions[i] for i in combination] + attr_values_sum + [total_sum])

    # 调试输出以检查数据保存过程
    print("Data to save (initial combinations):", data_to_save)

    # 将初步组合保存到文件，增加“总和”列
    columns = ["\u523b\u53701", "\u523b\u53702", "\u523b\u53703", "\u653b\u51fb", "\u9632\u5fa1", "\u7279\u653b", "\u7279\u9632", "\u901f\u5ea6", "\u4f53\u529b", "\u603b\u548c"]
    df = pd.DataFrame(data_to_save, columns=columns)
    df.to_csv(combinations_file, index=False, encoding='utf-8')

    return initial_combinations

# 验证刻印组合是否符合所有条件（从文件中读取）
def validate_combinations(attribute_targets, attributes):
    valid_combinations = []
    try:
        df = pd.read_csv(combinations_file, encoding='utf-8')
    except FileNotFoundError:
        return valid_combinations

    # 调试输出以检查从文件中读取的数据
    print("Data loaded for validation:", df)

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
            valid_combinations.append([row["刻印1"], row["刻印2"], row["刻印3"], row["攻击"], row["防御"], row["特攻"], row["特防"], row["速度"], row["体力"], row["总和"]])

    # 调试输出以检查有效组合
    print("Valid combinations:", valid_combinations)

    return valid_combinations

# 修改 GUI 结果表格，增加总和列

def create_gui():
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle('刻印筛选工具')
    window.resize(1200, 800)  # 调大窗口尺寸
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

        def make_reset_function(min_field, max_field):
            def reset():
                min_field.setText("0")
                max_field.setText("0")
            return reset

        reset_button.clicked.connect(make_reset_function(min_field, max_field))
        row_layout.addWidget(reset_button)

        form_layout.addRow(row_layout)
        input_fields[index] = (min_field, max_field)

    monster_id_field = QLineEdit()
    form_layout.addRow('专属精灵ID:', monster_id_field)

    symmetric_checkbox = QCheckBox("对称")
    form_layout.addRow(symmetric_checkbox)

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
    form_layout.addRow(QLabel('选择刻印质量:'), quality_row_layout)

    total_sum_checkboxes = {}
    total_sum_conditions = {'大于220': '>220', '等于220': '=220', '小于220': '<220'}
    total_sum_row_layout = QHBoxLayout()
    for label, value in total_sum_conditions.items():
        checkbox = QCheckBox(label)
        if label == '大于220':
            checkbox.setChecked(True)
        total_sum_row_layout.addWidget(checkbox)
        total_sum_checkboxes[value] = checkbox
    form_layout.addRow(QLabel('选择总和条件（仅对5角刻印）:'), total_sum_row_layout)

    filter_button = QPushButton('筛选刻印组合')
    download_button = QPushButton('下载刻印数据')
    update_button = QPushButton('更新刻印文件')
    result_table = QTableWidget()
    result_table.setColumnCount(10)  # 原来是9，现在增加一列
    result_table.setHorizontalHeaderLabels(["刻印1", "刻印2", "刻印3", "攻击", "防御", "特攻", "特防", "速度", "体力", "总和"])

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
        filter_low_values = filter_low_values_checkbox.isChecked()
        quality_filter = [value for value, checkbox in quality_checkboxes.items() if checkbox.isChecked()]
        total_sum_filter = [value for value, checkbox in total_sum_checkboxes.items() if checkbox.isChecked()]

        try:
            mintmark_list = []
            with open(data_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    mintmark_list.append(row)
        except FileNotFoundError:
            QMessageBox.critical(window, "错误", f"文件 {data_file} 未找到，请先下载数据。")
            return

        filtered_mintmark_list = initial_filtering(mintmark_list, monster_id_filter=monster_id, quality_filter=quality_filter, filter_low_values=filter_low_values, total_sum_filter=total_sum_filter)
        filtered_mintmark_list = filter_zero_requirements(filtered_mintmark_list, attribute_targets)
        find_initial_combinations(filtered_mintmark_list, attribute_targets, symmetric=symmetric)
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
    create_gui()
