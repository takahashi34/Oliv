def export_to_origin(currentData, voltageData, lightData, filename, plot_type):
    import win32com.client
    import time

    # Select Origin columns according to the plot type.
    if plot_type == 'LI':
        column_names = ['Current', 'Power per facet']
        column_units = ['mA', 'mW']
        column_data = [currentData, lightData]

    elif plot_type == 'IV':
        column_names = ['Voltage', 'Current']
        column_units = ['V', 'mA']
        column_data = [voltageData, currentData]

    elif plot_type == 'LIV':
        column_names = ['Current', 'Power per facet', 'Voltage']
        column_units = ['mA', 'mW', 'V']
        column_data = [currentData, lightData, voltageData]

    else:
        raise ValueError(f'Unsupported plot type: {plot_type}')

    origin = win32com.client.DispatchEx("Origin.ApplicationSI")
    origin.Visible = True

    time.sleep(1)

    # Correct template name
    cleanFilename = filename.replace("_", "_")
    pageName = origin.CreatePage(2, cleanFilename, "Origin")

    # Create the required number of Origin columns.
    origin.Execute(f"wks.ncols = {len(column_names)};")

    # Set each column name and unit.
    for i in range(len(column_names)):
        column_number = i + 1

        origin.Execute(
            f'wks.col{column_number}.lname$ = "{column_names[i]}";'
        )
        origin.Execute(
            f'wks.col{column_number}.unit$ = "{column_units[i]}";'
        )

    # Prepare worksheet rows in the selected column order.
    data = []

    for i in range(len(column_data[0])):
        row = []

        for one_column in column_data:
            row.append(one_column[i])

        data.append(row)

    success = origin.PutWorksheet(pageName, data, 0, 0)

    print("Success:", success)
    print("Page:", pageName)

    # Force it to show
    origin.Execute(f'page.active$="{pageName}";')
    origin.Execute("doc -mc 1;")
