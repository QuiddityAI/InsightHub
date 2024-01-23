<script setup>
</script>

<script>

export default {
  data() {
    return {
    }
  }
}

</script>

<template>
  <div class="max-w-screen-lg mx-auto my-12">
    <div class="bg-gray-200 rounded-xl shadow-md px-6 py-2 mb-6">
      <h1 class="text-xl font-bold">A tool that offers some kind of search</h1>
    </div>

    <p>Here is an example of an external search page.</p>
    <p>It is a Vue component, and can be found at <code>frontend/src/ExternalSearchExample.vue</code>.</p>
    <br>

    <div class="flex flex-row">
      <div class="flex-none w-64 mr-4">
        <div class="flex flex-col bg-gray-200 pl-2 pt-1 pb-2">
          Search Filters:
          <ul class="list-disc pl-4">
            <li>Filter 1</li>
            <li>Filter 2</li>
            <li>Filter 3</li>
          </ul>
          <br>
          More Filters:
          <ul class="list-disc pl-4">
            <li>Filter 1</li>
            <li>Filter 2</li>
            <li>Filter 3</li>
          </ul>
        </div>
      </div>
      <div class="flex-1">
        <!-- search bar with rounded corners, full width -->
        <div class="flex-1 h-9 flex flex-row items-center mb-4">
          <span class="mr-4">Search:</span>
          <input type="search" name="search" @search=""
          :placeholder="`Describe what you want to find`"
          class="w-full h-full rounded-md border-0 py-1.5 text-gray-900 ring-1
        ring-inset ring-gray-300 placeholder:text-gray-400
        focus:ring-2 focus:ring-inset focus:ring-blue-400
        sm:text-sm sm:leading-6 shadow-sm" />
        </div>

        <iframe
          allowfullscreen="true"
          src="embed.html?dataset_id=6&map_id=72fb88b3e8159ad275364753fe7a4b00"

          _option_without_access_to_their_db_src="absclust.com/embed.html?item_set=www.xyz_tool.com/result_set_1234.json"

          _option_with_access_to_their_db_src="absclust.com/embed.html?client=xyz_tool&item_ids=1234,5678,9012"

          _option_with_access_to_their_db_and_query_src="absclust.com/embed.html?client=xyz_tool&query=mxene"

          _option_with_our_db_and_query_src="absclust.com/embed.html?query=mxene"

          width="100%"
          style="max-width: 1200px; min-height: 500px"
        >
        </iframe>

        <br>
        <div v-for="item in 10" class="bg-gray-100 rounded-xl px-6 py-2 mb-6">
          <h1 class="text-xl font-bold">Result {{ item }}: Lorem Ipsum</h1>
          <p>Lorem Ipsum is simply dummy text of the printing and typesetting industry.</p>

        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>

</style>
