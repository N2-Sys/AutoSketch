cmake_minimum_required(VERSION 3.6)

option(IS_SWITCH "Is building switch programs" ON)

if(${IS_SWITCH})
	project(AutoSketch LANGUAGES)
	message(STATUS "Building switch programs.")
else()
	project(AutoSketch)
	message(STATUS "Building host programs.")
endif()

function(add_p4 name source)
	if(${IS_SWITCH})
		make_directory("${CMAKE_CURRENT_BINARY_DIR}/${name}.build")

		add_custom_command(
			OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/${name}.sh"

			# COMMAND rm -rf *
			COMMAND cmake \"$ENV{SDE}/p4studio\"
			-DCMAKE_INSTALL_PREFIX=\"$ENV{SDE_INSTALL}\"
			-DCMAKE_MODULE_PATH=\"$ENV{SDE}/cmake\"
			-DP4_NAME=\"as_${name}\"
			-DP4_PATH=\"${CMAKE_CURRENT_SOURCE_DIR}/${source}\"
			COMMAND make
		)

		add_custom_target(${name} ALL
			DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/${name}.sh"
		)
	endif()
endfunction()

add_subdirectory(apps)