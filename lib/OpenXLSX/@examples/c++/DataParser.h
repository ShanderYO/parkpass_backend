//
// Created by none on 19.06.19.
//

#pragma once

#include <vector>
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"

using namespace std;
using namespace rapidjson;



class DataParser {
    public:
        static std::vector<std::vector<std::string>> parse(const std::string & path);
};

//class SheetRows {
//    public:
//        SheetRows(const char& row);
//
//    private:
//        std::vector<std::vector<char *>> row_data;
//};
