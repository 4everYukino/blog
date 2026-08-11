---
layout: post
title: to_upper_copy VS transform
author: Bruce
tag: 技术
---

## 结论

虽然 `to_upper_copy` 开销更大，但：

* 适用性更为广泛，还可以处理如 `vector<char>` 的情况（虽然不太可能这么用）。
* 较为安全，存在对于迭代器是否有效的检查。

仅对于一般情况，也即得到一个 `uppercase` 的 `string`，使用 `transform` 封装一个方法即可。

## 问题

C++ 的 string 库并没有 upper 方法，一般用 `boost::to_upper` / `boost::to_upper_copy` 代替。

而 `boost::to_upper_copy` 却并不接收 `const char*` 的输入，定义如下：

```
......
        //! Convert to upper case

        /*!

            \overload

        */

        template<typename SequenceT>

        inline SequenceT to_upper_copy(

            const SequenceT& Input,

            const std::locale& Loc=std::locale())

        {

            return ::boost::algorithm::detail::transform_range_copy<SequenceT>(

                Input,

                ::boost::algorithm::detail::to_upperF<

                    typename range_value<SequenceT>::type >(Loc));

        }
......
```

原因：
* 它无法根据 `const char*` 构造一个 `range`。
* 它无法返回 `const char*` 副本。

参考：

> https://stackoverflow.com/questions/5343193/boost-to-upper-char-pointer-in-one-expression

简单直观的办法，就是 `to_upper_copy<string>(ptr)`，但是这样又将导致 `const char*` 隐式转化为 `string`，在循环量大的时候导致多余构造。

经 reviewer 提醒，应该使用 `transform` 方法，其定义非常直观：

```
......
  /**

   *  @brief Perform an operation on a sequence.

   *  @ingroup mutating_algorithms

   *  @param  __first     An input iterator.

   *  @param  __last      An input iterator.

   *  @param  __result    An output iterator.

   *  @param  __unary_op  A unary operator.

   *  @return   An output iterator equal to @p __result+(__last-__first).

   *

   *  Applies the operator to each element in the input range and assigns

   *  the results to successive elements of the output sequence.

   *  Evaluates @p *(__result+N)=unary_op(*(__first+N)) for each @c N in the

   *  range @p [0,__last-__first).

   *

   *  @p unary_op must not alter its argument.

  */

  template<typename _InputIterator, typename _OutputIterator,

     typename _UnaryOperation>

    _GLIBCXX20_CONSTEXPR

    _OutputIterator

    transform(_InputIterator __first, _InputIterator __last,

        _OutputIterator __result, _UnaryOperation __unary_op)

    {

      // concept requirements

      __glibcxx_function_requires(_InputIteratorConcept<_InputIterator>)

      __glibcxx_function_requires(_OutputIteratorConcept<_OutputIterator,

      // "the type returned by a _UnaryOperation"

      __typeof__(__unary_op(*__first))>)

      __glibcxx_requires_valid_range(__first, __last);



      for (; __first != __last; ++__first, (void)++__result)

  *__result = __unary_op(*__first);

      return __result;

    }
......
```

但是它有一个问题：不检查 `__result` 是否有效，若 `__result` 指向一个无法扩容的容器（如固定大小的 `char buffer[]`），将存在越界风险。

我于本机 (CPU: i5-13490F) 测试其循环 `1000W` 的情况下：

```
to_upper_copy:
Cost 3934ms in total.
transform:
Cost 504ms in total.
```

粗略计算下，性能约为 8 倍左右。

## 简单原因

可以分别编译出两个版本的可执行文件，使用 gprof 进行简单分析（上面循环 `1000W` 次就是为了这里的得到一个更直观的时间）：

### to_upper_copy

```
Each sample counts as 0.01 seconds.
  %   cumulative   self              self     total
 time   seconds   seconds    calls   s/call   s/call  name
  8.89      0.20     0.20 150000000     0.00     0.00  bool boost::iterators::iterator_core_access::equal<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default> >(boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default> const&, boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default> const&, mpl_::bool_<true>)
  7.11      0.36     0.16 10000000     0.00     0.00  void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default> >(boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, std::input_iterator_tag)
  6.89      0.52     0.15 130000000     0.00     0.00  std::ctype<char>::toupper(char) const
  6.22      0.66     0.14 280000000     0.00     0.00  boost::iterators::iterator_adaptor<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, char, boost::use_default, char, boost::use_default>::base() const
  6.00      0.79     0.14 130000000     0.00     0.00  boost::algorithm::detail::to_upperF<char>::operator()(char) const
  5.11      0.91     0.12 150000000     0.00     0.00  bool __gnu_cxx::operator==<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >(__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > const&, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > const&)
  5.11      1.02     0.12 130000000     0.00     0.00  boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>::dereference() const
  4.89      1.13     0.11 130000000     0.00     0.00  void boost::iterators::iterator_core_access::increment<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default> >(boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>&)
  4.44      1.23     0.10 130000000     0.00     0.00  __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >::operator++()
  4.00      1.32     0.09 150000000     0.00     0.00  bool boost::iterators::iterator_adaptor<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, char, boost::use_default, char, boost::use_default>::equal<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, char, boost::use_default, char, boost::use_default>(boost::iterators::iterator_adaptor<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, char, boost::use_default, char, boost::use_default> const&) const
  3.56      1.40     0.08 130000000     0.00     0.00  char std::toupper<char>(char, std::locale const&)
  3.56      1.48     0.08                             _init
  3.33      1.55     0.07 130000000     0.00     0.00  boost::iterators::iterator_adaptor<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, char, boost::use_default, char, boost::use_default>::increment()
  3.11      1.62     0.07 300000000     0.00     0.00  __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >::base() const
  3.11      1.70     0.07 260000000     0.00     0.00  boost::iterators::detail::iterator_facade_base<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, char, boost::iterators::random_access_traversal_tag, char, long, false, false>::derived()
  2.67      1.75     0.06 150000000     0.00     0.00  boost::iterators::detail::enable_if_interoperable<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, boost::mpl::apply2<boost::iterators::detail::always_bool2, boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default> >::type>::type boost::iterators::operator!=<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, char, boost::iterators::random_access_traversal_tag, char, long, boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, char, boost::iterators::random_access_traversal_tag, char, long>(boost::iterators::iterator_facade<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, char, boost::iterators::random_access_traversal_tag, char, long> const&, boost::iterators::iterator_facade<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, char, boost::iterators::random_access_traversal_tag, char, long> const&)
  2.67      1.81     0.06 130000000     0.00     0.00  boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>::reference boost::iterators::iterator_core_access::dereference<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default> >(boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default> const&)
  2.67      1.88     0.06 130000000     0.00     0.00  __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >::operator*() const
  2.44      1.93     0.06 130000000     0.00     0.00  boost::iterators::detail::iterator_facade_base<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, char, boost::iterators::random_access_traversal_tag, char, long, false, false>::operator*() const
  2.22      1.98     0.05 130000000     0.00     0.00  boost::iterators::detail::iterator_facade_base<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, char, boost::iterators::random_access_traversal_tag, char, long, false, false>::operator++()
  1.78      2.02     0.04 130000000     0.00     0.00  boost::iterators::detail::iterator_facade_base<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, char, boost::iterators::random_access_traversal_tag, char, long, false, false>::derived() const
  1.33      2.05     0.03 20000000     0.00     0.00  boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default> boost::iterators::make_transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > >(__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::algorithm::detail::to_upperF<char>)
  1.33      2.08     0.03 10000000     0.00     0.00  void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default> >(boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>)
  1.33      2.11     0.03 10000000     0.00     0.00  void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct_aux<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default> >(boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, std::__false_type)
  1.11      2.13     0.03        1     0.03     0.03  std::char_traits<char>::length(char const*)
  0.89      2.15     0.02 10000000     0.00     0.00  boost::range_iterator<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, void>::type boost::range_detail::range_end<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const>(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&)
  0.89      2.17     0.02 10000000     0.00     0.00  std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > boost::algorithm::to_upper_copy<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&, std::locale const&)
  0.67      2.19     0.01 150000000     0.00     0.00  boost::integral_constant<bool, true>::operator mpl_::bool_<true> const&() const
  0.44      2.20     0.01 20000000     0.00     0.00  boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>::transform_iterator(__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > const&, boost::algorithm::detail::to_upperF<char>)
  0.44      2.21     0.01 10000000     0.00     0.00  boost::range_iterator<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, void>::type boost::range_detail::range_begin<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const>(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&)
  0.44      2.22     0.01 10000000     0.00     0.00  boost::range_iterator<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, void>::type boost::range_adl_barrier::begin<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&)
  0.44      2.23     0.01 10000000     0.00     0.00  std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > boost::algorithm::detail::transform_range_copy<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, boost::algorithm::detail::to_upperF<char> >(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&, boost::algorithm::detail::to_upperF<char>)
  0.44      2.24     0.01 10000000     0.00     0.00  std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, void>(boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, std::allocator<char> const&)
  0.44      2.25     0.01        1     0.01     2.15  func_str()
  0.00      2.25     0.00 20000000     0.00     0.00  boost::iterators::iterator_adaptor<boost::iterators::transform_iterator<boost::algorithm::detail::to_upperF<char>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, boost::use_default, boost::use_default>, __gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, char, boost::use_default, char, boost::use_default>::iterator_adaptor(__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > const&)
  0.00      2.25     0.00 10000000     0.00     0.00  boost::range_iterator<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, void>::type boost::range_adl_barrier::end<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&)
  0.00      2.25     0.00 10000000     0.00     0.00  boost::algorithm::detail::to_upperF<char>::to_upperF(std::locale const&)
  0.00      2.25     0.00        1     0.00     0.03  __static_initialization_and_destruction_0(int, int)
  0.00      2.25     0.00        1     0.00     0.00  bool __gnu_cxx::__is_null_pointer<char const>(char const*)
  0.00      2.25     0.00        1     0.00     0.00  void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char const*>(char const*, char const*, std::forward_iterator_tag)
  0.00      2.25     0.00        1     0.00     0.03  std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string<std::allocator<char> >(char const*, std::allocator<char> const&)
  0.00      2.25     0.00        1     0.00     0.00  std::iterator_traits<char const*>::difference_type std::__distance<char const*>(char const*, char const*, std::random_access_iterator_tag)
  0.00      2.25     0.00        1     0.00     0.00  std::iterator_traits<char const*>::iterator_category std::__iterator_category<char const*>(char const* const&)
  0.00      2.25     0.00        1     0.00     0.00  std::iterator_traits<char const*>::difference_type std::distance<char const*>(char const*, char const*)
```

可以发现，这里有大量的时间耗费在了迭代器处理上，正好对应 `boost::to_upper_copy` 的实现方法，也即构造 `transform_iterator`，然后再用它们构造所需返回的 `SequenceT`。

如果 `input` 为一个 `const char*` 而不得不 `to_upper_copy<string>(input)` 的话，开销会更大一些，分析结果中将可以看到多出一个 `basic_string` 的构造。

### transform

```
Each sample counts as 0.01 seconds.
  %   cumulative   self              self     total
 time   seconds   seconds    calls  ms/call  ms/call  name
 28.95      0.11     0.11 10000000     0.00     0.00  __gnu_cxx::__normal_iterator<char*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > std::transform<char const*, __gnu_cxx::__normal_iterator<char*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, func_transform()::{lambda(char)#1}>(char const*, char const*, __gnu_cxx::__normal_iterator<char*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, func_transform()::{lambda(char)#1})
 26.32      0.21     0.10                             _init
 15.79      0.27     0.06 130000000     0.00     0.00  __gnu_cxx::__normal_iterator<char*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >::operator++()
 10.53      0.31     0.04 130000000     0.00     0.00  __gnu_cxx::__normal_iterator<char*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >::operator*() const
  7.89      0.34     0.03 130000000     0.00     0.00  func_transform()::{lambda(char)#1}::operator()(char) const
  7.89      0.37     0.03        1    30.00   270.00  func_transform()
  2.63      0.38     0.01        1    10.00    10.00  bool __gnu_cxx::__is_null_pointer<char const>(char const*)
  0.00      0.38     0.00        1     0.00    10.00  __static_initialization_and_destruction_0(int, int)
  0.00      0.38     0.00        1     0.00     0.00  std::char_traits<char>::length(char const*)
  0.00      0.38     0.00        1     0.00    10.00  void std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_construct<char const*>(char const*, char const*, std::forward_iterator_tag)
  0.00      0.38     0.00        1     0.00    10.00  std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::basic_string<std::allocator<char> >(char const*, std::allocator<char> const&)
  0.00      0.38     0.00        1     0.00     0.00  std::iterator_traits<char const*>::difference_type std::__distance<char const*>(char const*, char const*, std::random_access_iterator_tag)
  0.00      0.38     0.00        1     0.00     0.00  std::iterator_traits<char const*>::iterator_category std::__iterator_category<char const*>(char const* const&)
  0.00      0.38     0.00        1     0.00     0.00  std::iterator_traits<char const*>::difference_type std::distance<char const*>(char const*, char const*)
```

这里则比较简明直观，只是对各个元素不停地在调用 `toupper` 方法，我的 `input` 为 `Hello, World!`，共 13 个元素，循环了 `1000W` 次，正好对应调用次数。

这里还有一点比较有意思，传给 `tanrsform` 的是 `toupper` 函数，而这里退化为了一个匿名的 lambda 函数？可以看到是 `lambda(char)#1`。
