#include <iostream>
#include <chrono>
#include <iomanip>
#include <OpenXLSX/OpenXLSX.h>
#include <dirent.h>
#include <experimental/filesystem>
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include "DataParser.h"
#include "Writer.h"

using namespace std;
using namespace OpenXLSX;
using namespace rapidjson;

int main(int argc, char **argv)
{
    if (argc != 3) {
        cout <<  "Supply input and output dir, you, filthy animal!" << std::endl;
        exit(1);
    }

    std::string working_dir = std::string(argv[0]);
    working_dir = working_dir.substr(0, working_dir.find_last_of("/"));
    char* input_sheet_dir = argv[1];
    std::string output_file_dir = std::string(argv[2]);

    std::vector<std::string> sheets;

    DIR *dir;
    struct dirent *ent;
    if ((dir = opendir (input_sheet_dir)) != nullptr) {
        while ((ent = readdir (dir)) != nullptr) {
            char* name = ent->d_name;
            if (name[0] == '.') {
                continue;
            }

            sheets.emplace_back(name);
        }
        closedir (dir);
    } else {
        /* could not open directory */
        perror ("");
        return EXIT_FAILURE;
    }

    auto sw = SheetWriter(working_dir + "/output_restore_01.xlsm");


    for (std::string & sheet: sheets) {
        auto data = DataParser::parse(std::string(input_sheet_dir) + "/" + sheet);
        sw.writeSheet(sheet, data);
    }
    sw.finalize(output_file_dir);

    return 0;
}
