" 插件管理
call plug#begin('~/.vim/plugged')
Plug 'octol/vim-cpp-enhanced-highlight'
Plug 'preservim/nerdtree'
" 标签
Plug 'majutsushi/tagbar'
" 符号自动匹配
Plug 'jiangmiao/auto-pairs'
" ctags标签自动生成
Plug 'ludovicchabant/vim-gutentags'
" 代码格式化
Plug 'vim-autoformat/vim-autoformat'
" 由接口快速生成框架
Plug 'derekwyatt/vim-protodef'
Plug 'derekwyatt/vim-fswitch'
" .h and .cpp 快速切换
Plug 'vim-scripts/a.vim'
" 高亮设置
Plug 'mbriggs/mark.vim'
"Plug 'elzr/vim-json'
" Plug 'inkarkat/vim-mark'
Plug 'tikhomirov/vim-glsl'
call plug#end() 

" 插入模式下删除
" set backspace=indent,eol,start
set backspace=2
" 开启文件类别侦测
filetype on
" 根据侦测到的不同类型加载对应的插件
filetype plugin on


" 开启实时搜索功能
set incsearch
" 搜索时大小写不敏感
"set ignorecase
" 关闭兼容模式
set nocompatible
" vim 自身命令行模式智能补全
set wildmenu
" 设置自动换行
" set wrap

" 总是显示状态栏
set laststatus=2
" 显示光标当前位置
set ruler
" 高亮显示当前行/列
"set cursorline
"set cursorcolumn
" 高亮显示搜索结果
set hlsearch
" 设置默认显示行号
set number
" 开启语法高亮功能
syntax enable


" 代码缩进
" 自适应不同语言的智能缩进
filetype indent on
" 将制表符扩展为空格
set expandtab
" 设置编辑时制表符占用的空格数
set tabstop=4
" 设置格式化时制表符占用的空格数
set shiftwidth=4
" 让vim把连续数量的空格视为一个制表符
"set softtabstop=4

" 设置 tagbar 子窗口的位置出现在主编辑区的左边
" let tagbar_left=1
nnoremap <F8> :TagbarToggle<CR>
" 设置标签子窗口的宽度
let tagbar_width=32
" tagbar 子窗口中不显示冗余帮助信息
let g:tagbar_compact=1
" 设置 ctags 对哪些代码标识符生成标签
let g:tagbar_type_cpp = {
    \ 'kinds' : [
         \ 'c:classes:0:1',
         \ 'd:macros:0:1',
         \ 'e:enumerators:0:0',
         \ 'f:functions:0:1',
         \ 'g:enumeration:0:1',
         \ 'l:local:0:1',
         \ 'm:members:0:1',
         \ 'n:namespaces:0:1',
         \ 'p:functions_prototypes:0:1',
         \ 's:structs:0:1',
         \ 't:typedefs:0:1',
         \ 'u:unions:0:1',
         \ 'v:global:0:1',
         \ 'x:external:0:1'
     \ ],
     \ 'sro'        : '::',
     \ 'kind2scope' : {
         \ 'g' : 'enum',
         \ 'n' : 'namespace',
         \ 'c' : 'class',
         \ 's' : 'struct',
         \ 'u' : 'union'
     \ },
     \ 'scope2kind' : {
         \ 'enum'      : 'g',
         \ 'namespace' : 'n',
         \ 'class'     : 'c',
         \ 'struct'    : 's',
         \ 'union'     : 'u'
     \ }
\ }

" gutentags搜索工程目录的标志，碰到这些文件/目录名就停止向上一级目录递归 "
" ctags跳转不自动选择
map <c-]> g<c-]>
let g:gutentags_project_root = ['.root', '.svn', '.git', '.project']

" 所生成的数据文件的名称 "
let g:gutentags_ctags_tagfile = '.tags'

" 将自动生成的 tags 文件全部放入 ~/.cache/tags 目录中，避免污染工程目录 "
let s:vim_tags = expand('~/.cache/tags')
let g:gutentags_cache_dir = s:vim_tags
" 检测 ~/.cache/tags 不存在就新建 "
if !isdirectory(s:vim_tags)
   silent! call mkdir(s:vim_tags, 'p')
endif

" 配置 ctags 的参数 "
let g:gutentags_ctags_extra_args = ['--fields=+niazS', '--extra=+q']
let g:gutentags_ctags_extra_args += ['--c++-kinds=+pxI']
let g:gutentags_ctags_extra_args += ['--c-kinds=+px']
" 禁用gutentags自动加载gtags数据库的行为
let g:gutentags_auto_add_gtags_cscope = 0

" auto-format配置
noremap <F1> :Autoformat<CR>
" au BufWrite *.cpp, *.h :Autoformat
" let g:autoformat_autoindent = 0
" let g:autoformat_retab = 0
" let g:autoformat_remove_trailing_spaces = 0
"let g:formatdef_clangformat_google = '"clang-format -style google -"'
let g:formatdef_clangformat_google = '"astyle -SKpnfUHk1s4 --style=allman"'
let g:formatters_c = ['clangformat_google']
let g:formatters_cpp = ['clangformat_google']

" 接口快速生成框架设置
" 接口与实现快速切换
nmap <silent> <Leader>sw :FSHere<cr>
" 设置pullproto.pl 脚本路径
nmap <buffer> <silent> <leader> ,PP
let g:protodefprotogetter='~/.vim/plugged/vim-protodef/pullproto.pl'
"成员函数的实现顺序与声明顺序一致
let g:disable_protodef_sorting=1


" 设置快捷键
nnoremap <F3> :NERDTreeToggle<CR>
" .h with .cpp 快速切换
nnoremap <silent> <F2> :A<CR>
map <F4> <Esc>:%!jq .<CR>
