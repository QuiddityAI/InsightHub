<script setup>
import MainNavigation from './components/MainNavigation.vue';
</script>

<script>

export default {
  data() {
    return {
      available_databases: [
        {id: "absclust", title: "AbsClust Database", subtitle: "60 Million Documents"},
        {id: "pubmed", title: "PubMed Database", subtitle: "5 Mio. Documents (of 20M)"},
      ],
      database_information: {
        "absclust": "60 Million Documents",
        "pubmed": "5 Mio. Documents (of 20M)",
      },
      selected_database: "absclust",
    }
  }
}

</script>

<template>
  <MainNavigation/>
</template>

<style scoped>

</style>
