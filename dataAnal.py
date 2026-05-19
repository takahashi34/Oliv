def export_to_origin(currentData, voltageData, lightData, filename):
    import win32com.client
    import time

    origin = win32com.client.DispatchEx("Origin.ApplicationSI")
    origin.Visible = True

    time.sleep(1)

    # Correct template name
    cleanFilename = filename.replace("_", "_")
    pageName = origin.CreatePage(2, cleanFilename, "Origin")

    # Make sure columns exist
    origin.Execute("wks.ncols = 3;")
    origin.Execute('wks.col1.lname$ = "Current";')
    origin.Execute('wks.col2.lname$ = "Power per facet";')
    origin.Execute('wks.col3.lname$ = "Voltage";')
    origin.Execute('wks.col1.unit$ = "mA";')
    origin.Execute('wks.col2.unit$ = "mW";')
    origin.Execute('wks.col3.unit$ = "V";') 

    # Prepare data
    data = [
        [currentData[i], lightData[i], voltageData[i]]
        for i in range(len(currentData))
    ]

    success = origin.PutWorksheet(pageName, data, 0, 0)

    print("Success:", success)
    print("Page:", pageName)

    # Force it to show
    origin.Execute(f'page.active$="{pageName}";')
    origin.Execute("doc -mc 1;")
