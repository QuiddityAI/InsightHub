<script setup></script>

<script>
export default {
  data() {
    return {
      search_query: "",
      embedded_map_url: "embedded_map.html?dataset_id=6",
    }
  },
  methods: {
    execute_search() {
      if (this.search_query == "") {
        this.embedded_map_url = "embedded_map.html?dataset_id=6"
      } else {
        this.embedded_map_url =
          "embedded_map.html?dataset_id=6&query=" + encodeURIComponent(this.search_query)
      }
    },
  },
}
</script>

<template>
  <div class="mx-auto my-12 max-w-screen-lg">
    <div class="mb-6 rounded-xl bg-gray-200 px-6 py-2 shadow-md">
      <h1 class="text-xl font-bold">A tool that offers some kind of search</h1>
    </div>

    <p>Here is an example of an external search page.</p>
    <p>
      It is a Vue component, and can be found at
      <code>frontend/src/ExternalSearchExample.vue</code>.
    </p>
    <br />

    <div class="flex flex-row">
      <div class="mr-4 w-64 flex-none">
        <div class="flex flex-col bg-gray-200 pb-2 pl-2 pt-1">
          Search Filters:
          <ul class="list-disc pl-4">
            <li>Filter 1</li>
            <li>Filter 2</li>
            <li>Filter 3</li>
          </ul>
          <br />
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
        <div class="mb-4 flex h-9 flex-1 flex-row items-center">
          <span class="mr-4">Search:</span>
          <input
            type="search"
            name="search"
            @search="execute_search"
            v-model="search_query"
            :placeholder="`Describe what you want to find`"
            class="h-full w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
        </div>

        <iframe
          allowfullscreen="true"
          :src="embedded_map_url"
          _option_without_access_to_their_db_src="absclust.com/embed.html?item_set=www.xyz_tool.com/result_set_1234.json"
          _option_with_access_to_their_db_src="absclust.com/embed.html?client=xyz_tool&item_ids=1234,5678,9012"
          _option_with_access_to_their_db_and_query_src="absclust.com/embed.html?client=xyz_tool&query=mxene"
          _option_with_our_db_and_query_src="absclust.com/embed.html?query=mxene"
          width="100%"
          style="max-width: 1200px; min-height: 500px">
        </iframe>

        <br />
        <div v-for="item in 10" class="mb-6 rounded-xl bg-gray-100 px-6 py-2">
          <h1 class="text-xl font-bold">Result {{ item }}: Lorem Ipsum</h1>
          <p>Lorem Ipsum is simply dummy text of the printing and typesetting industry.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
