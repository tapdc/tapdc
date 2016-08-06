
#include <server.hpp>

int main(int argc, char** argv){
	string html = http_connection::render_html(argv[1]);
	base::print(html);
}
