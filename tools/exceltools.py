import pandas as pd
from typing import List, Optional, Union


def read_excel_sheet_as_list(file_path: str,
                             sheet_name: str,
                             filter_condition: Optional[str] = None,
                             target_column: Union[str, int] = 0,
                             limit: Optional[int] = None,
                             **kwargs) -> List:
    """
    读取Excel表格中指定子表格的数据，始终返回列表形式

    参数:
    file_path: Excel文件路径
    sheet_name: 子表格名称
    filter_condition: 筛选条件，支持以下格式：
        - "column_name=value": 筛选指定列等于特定值的目标列数据
        - "column_name!=value": 筛选指定列不等于特定值的目标列数据
        - "blank_column_name": 筛选指定列为空的目标列数据
        - "non_blank_column_name": 筛选指定列非空的目标列数据
        - 自定义条件字符串（Pandas查询语法）
    target_column: 要返回的目标列，可以是列名（str）或列索引（int），默认为第一列
    limit: 限制返回的数据数量，None表示返回全部数据
    **kwargs: pandas.read_excel的其他参数

    返回:
    List: 读取的数据列表
    """
    try:
        # 读取Excel文件中的指定子表格
        df = pd.read_excel(file_path, sheet_name=sheet_name, **kwargs)

        # 如果没有筛选条件，返回目标列的列表形式
        if filter_condition is None:
            if isinstance(target_column, str) and target_column in df.columns:
                result_data = df[target_column].dropna()
            else:
                result_data = df.iloc[:, target_column].dropna()

            # 应用数量限制
            if limit is not None and limit > 0:
                result_data = result_data.head(limit)
            return result_data.tolist()

        # 根据筛选条件进行数据过滤
        filtered_df = None

        # 先检查特殊前缀条件
        if filter_condition.startswith('blank_'):
            column_name = filter_condition[6:]  # 去掉 "blank_" 前缀
            if column_name in df.columns:
                filtered_df = df[df[column_name].isna()]
            else:
                print(f"excel-警告：未找到列名 '{column_name}'")

        elif filter_condition.startswith('non_blank_'):
            column_name = filter_condition[10:]  # 去掉 "non_blank_" 前缀
            if column_name in df.columns:
                filtered_df = df[df[column_name].notna()]
            else:
                print(f"excel-警告：未找到列名 '{column_name}'")

        # 然后检查等号和不等号条件
        elif '!=' in filter_condition:
            parts = filter_condition.split('!=', 1)
            if len(parts) == 2:
                column_name = parts[0].strip()
                target_value = parts[1].strip()
                if column_name in df.columns:
                    filtered_df = df[df[column_name] != target_value]
                else:
                    print(f"excel-警告：未找到列名 '{column_name}'")

        elif '=' in filter_condition:
            parts = filter_condition.split('=', 1)
            if len(parts) == 2:
                column_name = parts[0].strip()
                target_value = parts[1].strip()
                if column_name in df.columns:
                    filtered_df = df[df[column_name] == target_value]
                else:
                    print(f"excel-警告：未找到列名 '{column_name}'")

        else:
            # 使用自定义的pandas查询条件
            try:
                filtered_df = df.query(filter_condition)
            except Exception as e:
                print(f"excel-警告：筛选条件 '{filter_condition}' 无法解析: {e}")
                filtered_df = df

        # 如果找到了筛选条件对应的列，返回目标列数据
        result_data = None
        if filtered_df is not None and not filtered_df.empty:
            if isinstance(target_column, str) and target_column in filtered_df.columns:
                result_data = filtered_df[target_column].dropna()
            else:
                result_data = filtered_df.iloc[:, target_column].dropna()

            # 应用数量限制
            if limit is not None and limit > 0:
                result_data = result_data.head(limit)
            return result_data.tolist()
        else:
            print(f"excel-警告：筛选条件 '{filter_condition}' 无法应用或没有匹配数据")
            return []
    except FileNotFoundError:
        print(f"excel-错误：文件 '{file_path}' 未找到")
        return []
    except ValueError as e:
        print(f"excel-错误：未找到名为 '{sheet_name}' 的子表格")
        try:
            print(f"excel-可用子表格：{pd.ExcelFile(file_path).sheet_names}")
        except:
            pass
        return []
    except Exception as e:
        print(f"excel-读取Excel文件时发生错误：{e}")
        return []
def update_excel_status(file_path: str,
                        sheet_name: str,
                        target_list: List,
                        match_column: Union[str, int],
                        status_column: Union[str, int],
                        status_value: str = "处理",
                        **kwargs) -> bool:
    """
    修改Excel表格中指定行的状态

    参数:
    file_path: Excel文件路径
    sheet_name: 子表格名称
    target_list: 目标值列表，这些值用于在匹配列中查找对应的行
    match_column: 匹配列，可以是列名（str）或列索引（int），用于查找target_list中的值
    status_column: 状态列，可以是列名（str）或列索引（int），用于写入状态值
    status_value: 要写入的状态值，默认为"处理"
    **kwargs: pandas.read_excel的其他参数

    返回:
    bool: 操作是否成功
    """
    try:
        # 读取整个Excel文件
        excel_file = pd.ExcelFile(file_path)

        # 读取指定sheet
        df = pd.read_excel(file_path, sheet_name=sheet_name, **kwargs)

        # 创建原始数据的副本用于比较
        original_df = df.copy()

        # 根据match_column的类型处理匹配逻辑
        if isinstance(match_column, str):
            if match_column not in df.columns:
                print(f"excel-错误：未找到匹配列 '{match_column}'")
                return False
            match_series = df[match_column]
        else:
            if match_column >= len(df.columns):
                print(f"excel-错误：列索引 {match_column} 超出范围")
                return False
            match_series = df.iloc[:, match_column]

        # 根据status_column的类型确定状态列的位置
        if isinstance(status_column, str):
            if status_column not in df.columns:
                print(f"excel-错误：未找到状态列 '{status_column}'")
                return False
            status_col_name = status_column
        else:
            if status_column >= len(df.columns):
                print(f"excel-错误：列索引 {status_column} 超出范围")
                return False
            status_col_name = df.columns[status_column]

        # 找到匹配的行并更新状态
        updated_count = 0
        for target_value in target_list:
            # 查找匹配的行
            mask = match_series == target_value
            matching_rows = df[mask]

            if len(matching_rows) > 0:
                # 更新状态列的值
                df[status_col_name] = df[status_col_name].astype(str)
                df.loc[mask, status_col_name] = status_value
                updated_count += len(matching_rows)
                print(f"excel-已更新 '{target_value}' 的状态为 '{status_value}'，影响 {len(matching_rows)} 行")
            else:
                print(f"excel-警告：未找到匹配值 '{target_value}'")

        # 检查是否有实际修改
        if df.equals(original_df):
            print("excel-没有需要更新的数据")
            return True

        # 保存修改回Excel文件
        try:
            # 读取整个Excel文件的所有sheet
            with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                # 先保存所有其他sheet
                for sheet in excel_file.sheet_names:
                    if sheet != sheet_name:
                        # 读取原sheet数据并保存
                        other_df = pd.read_excel(file_path, sheet_name=sheet)
                        other_df.to_excel(writer, sheet_name=sheet, index=False)

                # 保存修改后的目标sheet
                df.to_excel(writer, sheet_name=sheet_name, index=False)

            print(f"excel-成功更新 {updated_count} 行数据到文件 '{file_path}'")
            return True

        except Exception as e:
            print(f"excel-保存文件时出错: {e}")
            # 如果使用append模式失败，尝试使用覆盖模式
            try:
                df.to_excel(file_path, sheet_name=sheet_name, index=False)
                print(f"excel-成功更新 {updated_count} 行数据到文件 '{file_path}'")
                return True
            except Exception as e2:
                print(f"excel-保存文件时再次出错: {e2}")
                return False

    except FileNotFoundError:
        print(f"excel-错误：文件 '{file_path}' 未找到")
        return False
    except ValueError as e:
        print(f"excel-错误：未找到名为 '{sheet_name}' 的子表格")
        try:
            print(f"excel-可用子表格：{pd.ExcelFile(file_path).sheet_names}")
        except:
            pass
        return False
    except Exception as e:
        print(f"excel-更新Excel文件时发生错误：{e}")
        return False


def update_excel_status_dict(file_path: str,
                        sheet_name: str,
                        target_list: List[dict],
                        match_column: Union[str, int],
                        status_column: Union[str, int],
                        status_value: str = "处理",
                        **kwargs) -> bool:
    """
    修改Excel表格中指定行的状态

    参数:
    file_path: Excel文件路径
    sheet_name: 子表格名称
    target_list: 目标字典列表，格式为 [{key: value}, {key1: value2}]，key为match_column匹配列的值，value为status_value状态列的值
    match_column: 匹配列，可以是列名（str）或列索引（int），用于查找target_list中的key值
    status_column: 状态列，可以是列名（str）或列索引（int），用于写入对应的value状态值
    status_value: 要写入的状态值，当target_list中的value为None时使用此默认值
    **kwargs: pandas.read_excel的其他参数

    返回:
    bool: 操作是否成功
    """
    try:
        # 读取整个Excel文件
        excel_file = pd.ExcelFile(file_path)

        # 读取指定sheet
        df = pd.read_excel(file_path, sheet_name=sheet_name, **kwargs)

        # 创建原始数据的副本用于比较
        original_df = df.copy()

        # 根据match_column的类型处理匹配逻辑
        if isinstance(match_column, str):
            if match_column not in df.columns:
                print(f"excel-错误：未找到匹配列 '{match_column}'")
                return False
            match_series = df[match_column]
        else:
            if match_column >= len(df.columns):
                print(f"excel-错误：列索引 {match_column} 超出范围")
                return False
            match_series = df.iloc[:, match_column]

        # 根据status_column的类型确定状态列的位置
        if isinstance(status_column, str):
            if status_column not in df.columns:
                print(f"excel-错误：未找到状态列 '{status_column}'")
                return False
            status_col_name = status_column
        else:
            if status_column >= len(df.columns):
                print(f"excel-错误：列索引 {status_column} 超出范围")
                return False
            status_col_name = df.columns[status_column]

        # 找到匹配的行并更新状态
        updated_count = 0
        for target_dict in target_list:
            if not isinstance(target_dict, dict):
                print(f"excel-警告：target_list中的元素不是字典格式: {target_dict}")
                continue

            for match_value, status_val in target_dict.items():
                # 使用传入的status_value参数作为默认值
                actual_status_value = status_val if status_val is not None else status_value

                # 查找匹配的行
                mask = match_series == match_value
                matching_rows = df[mask]

                if len(matching_rows) > 0:
                    # 更新状态列的值
                    df[status_col_name] = df[status_col_name].astype(str)
                    df.loc[mask, status_col_name] = actual_status_value
                    updated_count += len(matching_rows)
                    print(
                        f"excel-已更新匹配值 '{match_value}' 的状态为 '{actual_status_value}'，影响 {len(matching_rows)} 行")
                else:
                    print(f"excel-警告：未找到匹配值 '{match_value}'")

        # 检查是否有实际修改
        if df.equals(original_df):
            print("excel-没有需要更新的数据")
            return True

        # 保存修改回Excel文件
        try:
            # 读取整个Excel文件的所有sheet
            with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                # 先保存所有其他sheet
                for sheet in excel_file.sheet_names:
                    if sheet != sheet_name:
                        # 读取原sheet数据并保存
                        other_df = pd.read_excel(file_path, sheet_name=sheet)
                        other_df.to_excel(writer, sheet_name=sheet, index=False)

                # 保存修改后的目标sheet
                df.to_excel(writer, sheet_name=sheet_name, index=False)

            print(f"excel-成功更新 {updated_count} 行数据到文件 '{file_path}'")
            return True

        except Exception as e:
            print(f"excel-保存文件时出错: {e}")
            # 如果使用append模式失败，尝试使用覆盖模式
            try:
                df.to_excel(file_path, sheet_name=sheet_name, index=False)
                print(f"excel-成功更新 {updated_count} 行数据到文件 '{file_path}'")
                return True
            except Exception as e2:
                print(f"excel-保存文件时再次出错: {e2}")
                return False

    except FileNotFoundError:
        print(f"excel-错误：文件 '{file_path}' 未找到")
        return False
    except ValueError as e:
        print(f"excel-错误：未找到名为 '{sheet_name}' 的子表格")
        try:
            print(f"excel-可用子表格：{pd.ExcelFile(file_path).sheet_names}")
        except:
            pass
        return False
    except Exception as e:
        print(f"excel-更新Excel文件时发生错误：{e}")
        return False
def deduplicate_append_excel(file_path: str,
                             sheet_name: str,
                             target_list: List,
                             match_column: Union[str, int],
                             **kwargs) -> bool:
    """
    去重追加数据到Excel表格的指定列

    参数:
    file_path: Excel文件路径
    sheet_name: 子表格名称
    target_list: 要追加的数据列表
    match_column: 匹配列，可以是列名（str）或列索引（int），用于去重比较
    **kwargs: pandas.read_excel的其他参数

    返回:
    bool: 操作是否成功
    """
    try:
        # 读取整个Excel文件
        excel_file = pd.ExcelFile(file_path)

        # 读取指定sheet
        df = pd.read_excel(file_path, sheet_name=sheet_name, **kwargs)

        print(f"excel-原始数据行数: {len(df)}")
        print(f"excel-待追加数据量: {len(target_list)}")

        # 根据match_column的类型获取匹配列数据
        if isinstance(match_column, str):
            if match_column not in df.columns:
                print(f"excel-错误：未找到匹配列 '{match_column}'")
                print(f"excel-可用列名: {list(df.columns)}")
                return False
            existing_data = df[match_column].dropna().astype(str).tolist()
            column_name = match_column
        else:
            if match_column >= len(df.columns):
                print(f"excel-错误：列索引 {match_column} 超出范围")
                print(f"excel-总列数: {len(df.columns)}")
                return False
            existing_data = df.iloc[:, match_column].dropna().astype(str).tolist()
            column_name = df.columns[match_column]

        print(f"excel-列 '{column_name}' 中现有数据量: {len(existing_data)}")

        # 去重处理
        target_set = set(str(item) for item in target_list)
        existing_set = set(existing_data)

        print(f"excel-待追加数据去重后: {len(target_set)}")

        # 找出需要追加的新数据
        new_data = list(target_set - existing_set)

        print(f"excel-去重后需要追加的新数据量: {len(new_data)}")

        if not new_data:
            print("excel-没有需要追加的新数据")
            return True

        # 创建新数据行
        new_rows = []
        for value in new_data:
            new_row = {col: "" for col in df.columns}  # 创建空行
            new_row[column_name] = value  # 在目标列设置值
            new_rows.append(new_row)

        # 追加新数据到DataFrame
        new_df = pd.DataFrame(new_rows)
        df_updated = pd.concat([df, new_df], ignore_index=True)

        # 保存修改回Excel文件
        try:
            # 使用openpyxl引擎，替换模式保存
            with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                # 先保存所有其他sheet
                for sheet in excel_file.sheet_names:
                    if sheet != sheet_name:
                        other_df = pd.read_excel(file_path, sheet_name=sheet)
                        other_df.to_excel(writer, sheet_name=sheet, index=False)

                # 保存修改后的目标sheet
                df_updated.to_excel(writer, sheet_name=sheet_name, index=False)

            print(f"excel-成功追加 {len(new_data)} 行新数据到文件 '{file_path}'")
            print(f"excel-追加后总数据行数: {len(df_updated)}")
            return True

        except Exception as e:
            print(f"excel-保存文件时出错: {e}")
            # 如果使用append模式失败，尝试直接覆盖保存
            try:
                df_updated.to_excel(file_path, sheet_name=sheet_name, index=False)
                print(f"excel-成功追加 {len(new_data)} 行新数据到文件 '{file_path}'")
                return True
            except Exception as e2:
                print(f"excel-保存文件时再次出错: {e2}")
                return False

    except FileNotFoundError:
        print(f"excel-错误：文件 '{file_path}' 未找到")
        return False
    except ValueError as e:
        print(f"excel-错误：未找到名为 '{sheet_name}' 的子表格")
        try:
            print(f"excel-可用子表格：{pd.ExcelFile(file_path).sheet_names}")
        except:
            pass
        return False
    except Exception as e:
        print(f"excel-去重追加Excel文件时发生错误：{e}")
        import traceback
        traceback.print_exc()
        return False


# # 使用示例
# def example_usage():
#     """
#     使用示例
#     """
#     # 假设有一些子域名数据要追加
#     subdomains = ["test1.example.com", "test2.example.com", "test1.example.com"]  # 包含重复数据
#
#     success = deduplicate_append_excel(
#         file_path="info-auto.xlsx",
#         sheet_name="子域名",
#         target_list=subdomains,
#         match_column="名称"
#     )
#
#     if success:
#         print("数据追加成功！")
#     else:
#         print("数据追加失败！")


# # 使用示例
# if __name__ == "__main__":
#     # 读取示例
#     data_list = read_excel_sheet_as_list("../info-auto.xlsx", "子域名", "host处理状态!=处理")
#     print(f"excel-读取到的数据: {data_list}")
#
#     # 更新状态示例
#     success = update_excel_status(
#         file_path="../info-auto.xlsx",
#         sheet_name="子域名",
#         target_list=data_list,  # 使用读取到的列表
#         match_column="host",  # 假设host列用于匹配
#         status_column="host处理状态",  # 状态列名
#         status_value="处理"  # 要写入的状态值
#     )
#
#     if success:
#         print("状态更新成功")
#     else:
#         print("状态更新失败")