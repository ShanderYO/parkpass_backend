#=======================================================================================================================
# Define Demo1 target
#=======================================================================================================================
add_executable(Demo1 Demo1.cpp Writer.cpp Writer.h DataParser.cpp DataParser.h)
target_link_libraries(Demo1 PUBLIC OpenXLSX)
target_include_directories(Demo1 PUBLIC ${OPENXLSX_INSTALLDIR}/include)
set_target_properties(Demo1 PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${OPENXLSX_INSTALLDIR}/bin)

