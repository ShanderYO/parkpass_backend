//
// Created by none on 19.06.19.
//

#pragma once


#include <OpenXLSX/OpenXLSX.h>
#include "rapidjson/document.h"

using  namespace std;
using namespace OpenXLSX;
using namespace rapidjson;

class SheetWriter {

private:
    XLDocument doc;

public:
    void writeSheet(const std::string& sheet_name, const std::vector<std::vector<std::string>>& data);
    void finalize(std::string & output_file_name);

    explicit SheetWriter(const std::string& name);
};
