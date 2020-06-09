//
// Created by none on 19.06.19.
//

#include "Writer.h"


SheetWriter::SheetWriter(const std::string& name) {
    this->doc.OpenDocument(name);
}

void SheetWriter::writeSheet(const std::string &sheet_name, const std::vector<std::vector<std::string>> &data) {
    auto data_sheet = doc.Workbook().Worksheet(sheet_name);
    data_sheet.SetState(XLSheetState::Visible);

    int row = 1;
    for (auto & row_data : data) {
        int col = 1;
        for (auto & cells_data : row_data) {
            if (cells_data.empty()) {
                col++;
                continue;
            }
            data_sheet.Row(row).SetHidden(false);
            data_sheet.Cell(row, col).Value() = cells_data;
            col++;
        }
        row++;
    }
}

void SheetWriter::finalize(std::string & output_file_name) {
    this->doc.SaveDocumentAs(output_file_name);
}
