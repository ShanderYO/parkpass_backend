//
// Created by none on 19.06.19.
//

#include <fstream>
#include <iostream>
#include "DataParser.h"

std::vector<std::vector<std::string>> DataParser::parse(const std::string & path) {
    std::fstream fs;
    fs.open (path, std::fstream::in);

    if (!fs){
        std::cout << "no file " << path << std::endl;
        return std::vector<std::vector<std::string>>();
    }

    std::vector<std::vector<std::string>> sheet_data;

    char c;
    std::string char_buffer;
    std::vector<std::string> line_buffer;
    while (fs.get(c)) {
        if ((int)c == 29) {
            line_buffer.push_back(char_buffer);
            char_buffer.clear();
        } else if ((int)c == 12) {
            line_buffer.push_back(char_buffer);
            sheet_data.push_back(line_buffer);
            line_buffer.clear();
            char_buffer.clear();
        } else {
            char_buffer.push_back(c);
        }
    }

    return sheet_data;
//    fs.seekg (0, std::ifstream::end);
//    int length = fs.tellg();
//    fs.seekg (0, std::ifstream::beg);
//    char* json_string = new char[length];
//
//    fs.read(json_string, length);
//
//    Document d;
//    d.Parse(json_string);
//
//    StringBuffer buffer;
//    Writer<StringBuffer> writer(buffer);
//    d.Accept(writer);
//
//    std::cout << buffer.GetString() << std::endl;
//
//    fs.close();
}
